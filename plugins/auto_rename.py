from pyrogram import Client, filters
from pyrogram.types import Message, ForceReply  # Import ForceReply
from datetime import datetime
from helper.database import madflixbotz
from helper.utils import progress_for_pyrogram, humanbytes, convert
from config import Config
import os
import re

renaming_operations = {}

# Patterns for extracting episode numbers
episode_number_patterns = [
    re.compile(r'S(\d+)(?:E|EP)(\d+)'),  # Pattern 1: S01E02 or S01EP02
    re.compile(r'S(\d+)\s*(?:E|EP|-\s*EP)(\d+)'),  # Pattern 2: S01 E02 or S01 EP02 or S01 - E01 or S01 - EP02
    re.compile(r'(?:[([<{]?\s*(?:E|EP)\s*(\d+)\s*[)\]>}]?)'),  # Pattern 3: Episode Number After "E" or "EP"
    re.compile(r'(?:\s*-\s*(\d+)\s*)'),  # Pattern 3_2: episode number after -
    re.compile(r'S(\d+)[^\d]*(\d+)', re.IGNORECASE),  # Pattern 4: S2 09 ex.
    re.compile(r'(\d+)')  # Pattern X: Standalone Episode Number
]

# Pattern for extracting quality
quality_patterns = [
    re.compile(r'\b(?:.*?(\d{3,4}[^\dp]*p).*?|.*?(\d{3,4}p))\b', re.IGNORECASE),  # Pattern 5: 3-4 digits before 'p' as quality
    re.compile(r'[([<{]?\s*4k\s*[)\]>}]?', re.IGNORECASE),  # Pattern 6: Find 4k in brackets or parentheses
    re.compile(r'[([<{]?\s*2k\s*[)\]>}]?', re.IGNORECASE),  # Pattern 7: Find 2k in brackets or parentheses
    re.compile(r'[([<{]?\s*HdRip\s*[)\]>}]?|\bHdRip\b', re.IGNORECASE),  # Pattern 8: Find HdRip without spaces
    re.compile(r'[([<{]?\s*4kX264\s*[)\]>}]?', re.IGNORECASE),  # Pattern 9: Find 4kX264 in brackets or parentheses
    re.compile(r'[([<{]?\s*4kx265\s*[)\]>}]?', re.IGNORECASE)  # Pattern 10: Find 4kx265 in brackets or parentheses
]

def extract_episode_number(filename):
    for pattern in episode_number_patterns:
        match = re.search(pattern, filename)
        if match:
            return match.group(2)  # Extracted episode number
    return None

def extract_quality(filename):
    for pattern in quality_patterns:
        match = re.search(pattern, filename)
        if match:
            return match.group(0)  # Extracted quality
    return "Unknown"

async def auto_rename_files(client, message, file_id, file_name, media_type):
    user_id = message.from_user.id
    format_template = await madflixbotz.get_format_template(user_id)
    media_preference = await madflixbotz.get_media_preference(user_id)

    if not format_template:
        return await message.reply_text("Please Set An Auto Rename Format First Using /autorename")

    # Extract episode number and qualities
    episode_number = extract_episode_number(file_name)

    if episode_number:
        placeholders = ["episode", "Episode", "EPISODE", "{episode}"]
        for placeholder in placeholders:
            format_template = format_template.replace(placeholder, str(episode_number), 1)

        # Add extracted qualities to the format template
        quality_placeholders = ["quality", "Quality", "QUALITY", "{quality}"]
        for quality_placeholder in quality_placeholders:
            if quality_placeholder in format_template:
                extracted_qualities = extract_quality(file_name)
                if extracted_qualities == "Unknown":
                    await message.reply_text("I Was Not Able To Extract The Quality Properly. Renaming As 'Unknown'...")
                    return  # Exit if quality extraction fails

                format_template = format_template.replace(quality_placeholder, "".join(extracted_qualities))

        _, file_extension = os.path.splitext(file_name)
        new_file_name = f"{format_template}{file_extension}"
        file_path = f"downloads/{new_file_name}"
        file = message

        download_msg = await message.reply_text(text="Trying To Download.....")
        try:
            path = await client.download_media(message=file, file_name=file_path, progress=progress_for_pyrogram, progress_args=("Download Started....", download_msg, time.time()))
        except Exception as e:
            return await download_msg.edit(e)

        duration = 0
        try:
            metadata = extractMetadata(createParser(file_path))
            if metadata.has("duration"):
                duration = metadata.get('duration').seconds
        except Exception as e:
            print(f"Error getting duration: {e}")

        upload_msg = await download_msg.edit("Trying To Uploading.....")
        ph_path = None
        c_caption = await madflixbotz.get_caption(message.chat.id)
        c_thumb = await madflixbotz.get_thumbnail(message.chat.id)

        caption = c_caption.format(filename=new_file_name, filesize=humanbytes(message.document.file_size), duration=convert(duration)) if c_caption else f"**{new_file_name}**"

        if c_thumb:
            ph_path = await client.download_media(c_thumb)
            print(f"Thumbnail downloaded successfully. Path: {ph_path}")
        elif media_type == "video" and message.video.thumbs:
            ph_path = await client.download_media(message.video.thumbs[0].file_id)

        if ph_path:
            Image.open(ph_path).convert("RGB").save(ph_path)
            img = Image.open(ph_path)
            img.resize((320, 320))
            img.save(ph_path, "JPEG")

        try:
            if media_type == "document":
                await client.send_document(
                    message.chat.id,
                    document=file_path,
                    thumb=ph_path,
                    caption=caption,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started.....", upload_msg, time.time())
                )
            elif media_type == "video":
                await client.send_video(
                    message.chat.id,
                    video=file_path,
                    caption=caption,
                    thumb=ph_path,
                    duration=duration,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started.....", upload_msg, time.time())
                )
            elif media_type == "audio":
                await client.send_audio(
                    message.chat.id,
                    audio=file_path,
                    caption=caption,
                    thumb=ph_path,
                    duration=duration,
                    progress=progress_for_pyrogram,
                    progress_args=("Upload Started.....", upload_msg, time.time())
                )
        except Exception as e:
            os.remove(file_path)
            if ph_path:
                os.remove(ph_path)
            return await upload_msg.edit(f"Error: {e}")

        await download_msg.delete()
        os.remove(file_path)
        if ph_path:
            os.remove(ph_path)

    else:
        reply_msg = await message.reply_text("This file doesn't contain an episode number. Please reply with the desired new name.", reply_markup=ForceReply(True))
        renaming_operations.pop(file_id, None)
# Jishu Developer 
# Don't Remove Credit 🥺
# Telegram Channel @Madflix_Bots
# Developer @JishuDeveloper
