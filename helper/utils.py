import math
import time
from datetime import datetime
from pytz import timezone
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import Config, Txt

async def progress_for_pyrogram(current, total, update_type, message, start_time):
    try:
        now = time.time()
        elapsed_time = now - start_time
        if round(elapsed_time % 5.00) == 0 or current == total:
            percentage = current * 100 / total
            speed = current / elapsed_time
            estimated_total_time = (total - current) / speed

            progress_bar = generate_progress_bar(percentage)
            formatted_elapsed_time = format_time(elapsed_time * 1000)
            formatted_total_time = format_time(estimated_total_time * 1000)

            progress_message = (
                f"{update_type}\n\n"
                f"{progress_bar}{Txt.PROGRESS_BAR.format(percentage, humanbytes(current), humanbytes(total), humanbytes(speed), formatted_total_time)}"
            )

            await message.edit(
                text=progress_message,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✖️ Cancel ✖️", callback_data="close")]])
            )
    except Exception as e:
        print(f"Error in progress_for_pyrogram: {e}")

def generate_progress_bar(percentage):
    filled_blocks = ''.join(["⬢" for _ in range(math.floor(percentage / 5))])
    empty_blocks = ''.join(["⬡" for _ in range(20 - math.floor(percentage / 5))])
    return filled_blocks + empty_blocks

def format_time(milliseconds):
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    formatted_time = ((str(days) + "d, ") if days else "") + \
                     ((str(hours) + "h, ") if hours else "") + \
                     ((str(minutes) + "m, ") if minutes else "") + \
                     ((str(seconds) + "s, ") if seconds else "") + \
                     ((str(milliseconds) + "ms, ") if milliseconds else "")
    return formatted_time[:-2] 

def humanbytes(size):    
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'b'

async def send_log(bot, user):
    try:
        if Config.LOG_CHANNEL is not None:
            curr = datetime.now(timezone("Asia/Kolkata"))
            date = curr.strftime('%d %B, %Y')
            time = curr.strftime('%I:%M:%S %p')
            await bot.send_message(
                Config.LOG_CHANNEL,
                f"<b><u>New User Started The Bot</u></b> \n\n"
                f"<b>User ID</b> : `{user.id}` \n"
                f"<b>First Name</b> : {user.first_name} \n"
                f"<b>Last Name</b> : {user.last_name} \n"
                f"<b>User Name</b> : @{user.username} \n"
                f"<b>User Mention</b> : {user.mention} \n"
                f"<b>User Link</b> : <a href='tg://openmessage?user_id={user.id}'>Click Here</a>\n\n"
                f"Date: {date}\nTime: {time}\n\nBy: {bot.mention}"
            )
    except Exception as e:
        print(f"Error in send_log: {e}")

# Jishu Developer 
# Don't Remove Credit 🥺
# Telegram Channel @Madflix_Bots
# Developer @JishuDeveloper
