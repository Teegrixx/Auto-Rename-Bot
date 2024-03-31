import os
import re
import time
import asyncio
import logging
from datetime import datetime
from PIL import Image
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InputMediaDocument
from helper.utils import progress_for_pyrogram, humanbytes, convert
from helper.database import madflixbotz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define regular expressions for patterns
renaming_operations = {}
pattern_episode = re.compile(r'(?:S(\d+)[^\d]*(\d+))|(?:[([<{]?\s*(?:E|EP)\s*(\d+)\s*[)\]>}]?)|(?:\s*-\s*(\d+)\s*)|(\d+)')
pattern_quality = re.compile(r'\b(?:.*?(\d{3,4}[^\dp]*p).*?|.*?(\d{3,4}p))\b|\b(?:[([<{]?\s*(4k|2k|HdRip|4kX264|4kx265)\s*[)\]>}]?)', re.IGNORECASE)


async def download_file(client, message, file_path, progress_msg):
    try:
        with open(file_path, "wb") as file:
            await client.download_media(
                message=message,
                file=file,
                progress=progress_for_pyrogram,
                progress_args=("Download Started....", progress_msg, time.time())
            )
        return True
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return False


async def upload_file(client, chat_id, file_path, caption, media_type, duration, progress_msg):
    try:
        async with client:
            if media_type == "document":
                await client.send_document(
                    chat_id,
                    document=file_path,
                    caption=caption,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started.....", progress_msg, time.time())
                )
            elif media_type == "video":
                await client.send_video(
                    chat_id,
                    video=file_path,
                    caption=caption,
                    duration=duration,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started.....", progress_msg, time.time())
                )
            elif media_type == "audio":
                await client.send_audio(
                    chat_id,
                    audio=file_path,
                    caption=caption,
                    duration=duration,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started.....", progress_msg, time.time())
                )
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return False
    return True


def extract_information(filename):
    episode_number = None
    qualities = []

    for match in re.finditer(pattern_episode, filename):
        for group in match.groups():
            if group:
                episode_number = group
                break
        if episode_number:
            break

    for match in re.finditer(pattern_quality, filename):
        for group in match.groups():
            if group and group not in qualities:
                qualities.append(group)

    return episode_number, qualities


@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def auto_rename_files(client, message):
    user_id = message.from_user.id
    format_template = await madflixbotz.get_format_template(user_id)
    media_preference = await madflixbotz.get_media_preference(user_id)

    if not format_template:
        await message.reply_text("Please Set An Auto Rename Format First Using /autorename")
        return

    media_type = None
    if message.document:
        media_type = media_preference or "document"
    elif message.video:
        media_type = media_preference or "video"
    elif message.audio:
        media_type = media_preference or "audio"
    else:
        await message.reply_text("Unsupported File Type")
        return

    original_file_name = message.document.file_name if message.document else \
        (message.video.file_name + ".mp4") if message.video else \
        (message.audio.file_name + ".mp3")

    logger.info(f"Original File Name: {original_file_name}")

    if message.message_id in renaming_operations:
        elapsed_time = (datetime.now() - renaming_operations[message.message_id]).seconds
        if elapsed_time < 10:
            logger.info("File is being ignored as it is currently being renamed or was renamed recently.")
            return

    renaming_operations[message.message_id] = datetime.now()

    episode_number, qualities = extract_information(original_file_name)

    logger.info(f"Extracted Episode Number: {episode_number}")
    logger.info(f"Extracted Qualities: {qualities}")

    if not episode_number:
        await message.reply_text("Unable to extract episode number.")
        del renaming_operations[message.message_id]
        return

    new_file_name = format_template.replace("{episode}", str(episode_number))
    for quality in qualities:
        new_file_name = new_file_name.replace("{quality}", quality)

    _, file_extension = os.path.splitext(original_file_name)
    new_file_name += file_extension
    file_path = f"downloads/{new_file_name}"

    download_msg = await message.reply_text(text="Trying To Download.....")
    if not await download_file(client, message, file_path, download_msg):
        del renaming_operations[message.message_id]
        await download_msg.edit("Error downloading file.")
        return

    duration = 0
    try:
        metadata = extractMetadata(createParser(file_path))
        if metadata.has("duration"):
            duration = metadata.get('duration').seconds
    except Exception as e:
        logger.error(f"Error getting duration: {e}")

    upload_msg = await download_msg.edit("Trying To Uploading.....")
    c_caption = await madflixbotz.get_caption(message.chat.id)
    c_thumb = await madflixbotz.get_thumbnail(message.chat.id)

    caption = c_caption.format(filename=new_file_name, filesize=humanbytes(message.document.file_size),
                                duration=convert(duration)) if c_caption else f"**{new_file_name}**"

    ph_path = None
    if c_thumb:
        ph_path = await client.download_media(c_thumb)
    elif media_type == "video" and message.video.thumbs:
        ph_path = await client.download_media(message.video.thumbs[0].file_id)

    if ph_path:
        Image.open(ph_path).convert("RGB").save(ph_path)
        img = Image.open(ph_path)
        img.resize((320, 320))
        img.save(ph_path, "JPEG")

    if not await upload_file(client, message.chat.id, file_path, caption, media_type, duration, upload_msg):
        os.remove(file_path)
        if ph_path:
            os.remove(ph_path)
        del renaming_operations[message.message_id]
        await upload_msg.edit("Error uploading file.")
        return

    await download_msg.delete()
    os.remove(file_path)
    if ph_path:
        os.remove(ph_path)

    del renaming_operations[message.message_id]




# Jishu Developer
# Don't Remove Credit 🥺
# Telegram Channel @Madflix_Bots
# Developer @JishuDeveloper
