import asyncio
import time
import random
import nonebot
from nonebot import on_command, permission
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment, MessageEvent

pw_rooms = {}  # 用于存储创建的房间信息

create_room = on_command("创建房间", aliases={"建立房间"})
join_room = on_command("加入")
leave_room = on_command("退出")
start_match = on_command("开始匹配")
destroy_room = on_command("销毁房间", permission=permission.SUPERUSER)
list_rooms = on_command("查看所有房间")

def extract_args_create_room(msg: str):
    arg_list = msg.replace("创建房间", "").strip().split(" ")
    if len(arg_list) == 2:
        invite_code, rank = arg_list
        return invite_code, rank
    else:
        return None, None

def extract_args_join_room(msg: str):
    arg_list = msg.replace("加入", "").strip().split(" ")
    if len(arg_list) == 1:
        room_id = int(arg_list[0])
        return room_id
    else:
        return None

@create_room.handle()
async def handle_create_room(event: MessageEvent):
    msg = event.get_message().extract_plain_text()
    print(f"Debug: raw message: {msg}")  # 添加调试信息
    invite_code, rank = extract_args_create_room(msg)

    print(f"Debug: invite_code: {invite_code}, rank: {rank}")  # 添加调试信息

    if invite_code and rank:
        if rank in ["D", "D+", "C", "C+", "B", "B+", "A", "A+", "S"]:
            room_id = random.randint(10000, 99999)
            while room_id in pw_rooms:  # 确保房间ID是唯一的
                room_id = random.randint(10000, 99999)

            pw_rooms[room_id] = {
                "creator": event.user_id,
                "invite_code": invite_code,
                "rank": rank,
                "members": [event.user_id],
                "create_time": time.time(),
                "is_gaming": False,
            }
            await create_room.send(f"房间创建成功！房间ID：{room_id} | 邀请码：{invite_code} | 段位限制：{rank}")
        else:
            await create_room.finish("段位错误，请输入正确的段位")
    else:
        await create_room.finish("格式错误，请输入[创建房间 邀请码 段位]")

@join_room.handle()
async def handle_join_room(event: MessageEvent):
    msg = event.get_message().extract_plain_text()
    room_id = extract_args_join_room(msg)

    if room_id:
        if room_id not in pw_rooms:
            await join_room.finish("房间不存在，请检查房间ID")
        room = pw_rooms[room_id]
        if room["is_gaming"]:
            await join_room.finish("房间正在进行游戏，无法加入")

        for other_room_id, other_room in pw_rooms.items():
            if event.user_id in other_room["members"]:
                if other_room_id == room_id:
                    await join_room.finish("您已在房间内，请勿重复加入")
                else:
                    other_room["members"].remove(event.user_id)
                    await join_room.send(f"您已从房间{other_room_id}退出")

        if len(room["members"]) >= 5:
            await join_room.finish("房间已满，无法加入")
        room["members"].append(event.user_id)
        await join_room.send(f"加入房间成功！当前房间人数：{len(room['members'])}/5")
    else:
        await join_room.finish("格式错误，请输入[加入 <房间ID>]")

@leave_room.handle()
async def handle_leave_room(event: MessageEvent):
    for room_id, room in pw_rooms.items():
        if event.user_id in room["members"]:
            room["members"].remove(event.user_id)
            await leave_room.send(f"退出房间成功！房间ID：{room_id}")
            return
    await leave_room.finish("您当前不在任何房间内")

@start_match.handle()
async def handle_start_match(event: MessageEvent):
    for room_id, room in pw_rooms.items():
        if event.user_id == room["creator"]:
            room["is_gaming"] = True
            await start_match.send(f"房间{room_id}开始匹配！")
            return
    await start_match.finish("您当前没有创建任何房间")

@destroy_room.handle()
async def handle_destroy_room(event: MessageEvent):
    for room_id in list(pw_rooms.keys()):
        if event.user_id == pw_rooms[room_id]["creator"]:
            del pw_rooms[room_id]
            await destroy_room.send(f"房间{room_id}已销毁")
            return
    await destroy_room.finish("您当前没有创建任何房间")

@list_rooms.handle()
async def handle_list_rooms(event: MessageEvent):
    if not pw_rooms:
        await list_rooms.finish("当前没有可用的房间")
    msg = "当前房间列表：\n"
    for room_id, room in pw_rooms.items():
        if not room["is_gaming"]:
            msg += (
                f"房间ID：{room_id} | 邀请码：{room['invite_code']} | 段位限制：{room['rank']} | "
                f"队伍人数：{len(room['members'])}/5\n"
            )
    await list_rooms.send(msg)

async def clean_expired_room():
    while True:
        for room_id in list(pw_rooms.keys()):
            room = pw_rooms[room_id]
            if not room["is_gaming"] and time.time() - room["create_time"] > 15 * 60:
                creator = room["creator"]
                del pw_rooms[room_id]
                await nonebot.get_bot().send_private_msg(user_id=creator, message=f"房间{room_id}已超时销毁")
        await asyncio.sleep(60)

from nonebot import require

scheduler = require("nonebot_plugin_apscheduler").scheduler
scheduler.add_job(clean_expired_room, "interval", minutes=1)
