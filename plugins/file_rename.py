import asyncio
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message
from PIL import Image
from datetime import datetime
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from helper.utils import progress_for_pyrogram, humanbytes, convert
from helper.database import madflixbotz
from config import Config
import os
import re

renaming_operations = {}

# Define regular expressions to extract episode numbers and qualities from filenames
pattern1 = re.compile(r'S(\d+)(?:E|EP)(\d+)')
pattern2 = re.compile(r'S(\d+)\s*(?:E|EP|-\s*EP)(\d+)')
pattern3 = re.compile(r'(?:[([<{]?\s*(?:E|EP)\s*(\d+)\s*[)\]>}]?)')
pattern3_2 = re.compile(r'(?:\s*-\s*(\d+)\s*)')
pattern4 = re.compile(r'S(\d+)[^\d]*(\d+)', re.IGNORECASE)
patternX = re.compile(r'(\d+)')
pattern5 = re.compile(r'\b(?:.*?(\d{3,4}[^\dp]*p).*?|.*?(\d{3,4}p))\b', re.IGNORECASE)
pattern6 = re.compile(r'[([<{]?\s*4k\s*[)\]>}]?', re.IGNORECASE)
pattern7 = re.compile(r'[([<{]?\s*2k\s*[)\]>}]?', re.IGNORECASE)
pattern8 = re.compile(r'[([<{]?\s*HdRip\s*[)\]>}]?|\bHdRip\b', re.IGNORECASE)
pattern9 = re.compile(r'[([<{]?\s*4kX264\s*[)\]>}]?', re.IGNORECASE)
pattern10 = re.compile(r'[([<{]?\s*4kx265\s*[)\]>}]?', re.IGNORECASE)

# Define functions to extract quality and episode number using the defined regular expressions
async def extract_quality(filename):
    match5 = re.search(pattern5, filename)
    if match5:
        return match5.group(1) or match5.group(2)

    match6 = re.search(pattern6, filename)
    if match6:
        return "4k"

    match7 = re.search(pattern7, filename)
    if match7:
        return "2k"

    match8 = re.search(pattern8, filename)
    if match8:
        return "HdRip"

    match9 = re.search(pattern9, filename)
    if match9:
        return "4kX264"

    match10 = re.search(pattern10, filename)
    if match10:
        return "4kx265"

    return "Unknown"

async def extract_episode_number(filename):
    match = re.search(pattern1, filename)
    if match:
        return match.group(2)

    match = re.search(pattern2, filename)
    if match:
        return match.group(2)

    match = re.search(pattern3, filename)
    if match:
        return match.group(1)

    match = re.search(pattern3_2, filename)
    if match:
        return match.group(1)

    match = re.search(pattern4, filename)
    if match:
        return match.group(2)

    match = re.search(patternX, filename)
    if match:
        return match.group(1)

    return None

# Define the auto_rename_files handler using asyncio
@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def auto_rename_files(client, message):
    user_id = message.from_user.id
    format_template = await madflixbotz.get_format_template(user_id)
    media_preference = await madflixbotz.get_media_preference(user_id)

    if not format_template:
        return await message.reply_text("Please Set An Auto Rename Format First Using /autorename")

    # Extract information from the incoming file name
    if message.document:
        file_name = message.document.file_name
        media_type = media_preference or "document"
    elif message.video:
        file_name = f"{message.video.file_name}.mp4"
        media_type = media_preference or "video"
    elif message.audio:
        file_name = f"{message.audio.file_name}.mp3"
        media_type = media_preference or "audio"
    else:
        return await message.reply_text("Unsupported File Type")

    print(f"Original File Name: {file_name}")

    # Check whether the file is already being renamed or has been renamed recently
    file_id = message.document.file_id if message.document else message.video.file_id if message.video else message.audio.file_id
    if file_id in renaming_operations:
        elapsed_time = (datetime.now() - renaming_operations[file_id]).seconds
        if elapsed_time < 10:
            print("File is being ignored as it is currently being renamed or was renamed recently.")
            return

    # Mark the file as currently being renamed
    renaming_operations[file_id] = datetime.now()

    # Extract episode number and qualities
    episode_number = await extract_episode_number(file_name)
    print(f"Extracted Episode Number: {episode_number}")

    if episode_number:
        placeholders = ["episode", "Episode", "EPISODE", "{episode}"]
        for placeholder in placeholders:
            format_template = format_template.replace(placeholder, str(episode_number), 1)

        # Add extracted qualities to the format template
        quality_placeholders = ["quality", "Quality", "QUALITY", "{quality}"]
        for quality_placeholder in quality_placeholders:
            if quality_placeholder in format_template:
                extracted_qualities = await extract_quality(file_name)
                if extracted_qualities == "Unknown":
                    await message.reply_text("I Was Not Able To Extract The Quality Properly. Renaming As 'Unknown'...")
                    # Mark the file as ignored
                    del renaming_operations[file_id]
                    return

                format_template = format_template.replace(quality_placeholder, "".join(extracted_qualities))

        _, file_extension = os.path.splitext(file_name)
        new_file_name = f"{format_template}{file_extension}"
        file_path = f"downloads/{new_file_name}"

        download_msg = await message.reply_text(text="Trying To Download.....")
        try:
            download_task = asyncio.create_task(client.download_media(message=message, file_name=file_path, progress=progress_for_pyrogram))
            path = await asyncio.wait_for(download_task, timeout=30.0)
        except asyncio.TimeoutError:
            del renaming_operations[file_id]
            return await download_msg.edit("Download Timed Out.")

        duration = 0
        try:
            metadata = extractMetadata(createParser(file_path))
            if metadata.has("duration"):
                duration = metadata.get('duration').seconds
        except Exception as e:
            print(f"Error getting duration: {e}")

        upload_msg = await download_msg.edit("Trying To Uploading.....")

        caption = f"**{new_file_name}**"

        try:
            if media_type == "document":
                await client.send_document(
                    message.chat.id,
                    document=file_path,
                    caption=caption,
                    progress=progress_for_pyrogram
                )
            elif media_type == "video":
                await client.send_video(
                    message.chat.id,
                    video=file_path,
                    caption=caption,
                    thumb=None,
                    duration=duration,
                    progress=progress_for_pyrogram
                )
            elif media_type == "audio":
                await client.send_audio(
                    message.chat.id,
                    audio=file_path,
                    caption=caption,
                    thumb=None,
                    duration=duration,
                    progress=progress_for_pyrogram
                )
        except Exception as e:
            os.remove(file_path)
            del renaming_operations[file_id]
            return await upload_msg.edit(f"Error: {e}")

        await download_msg.delete()
        os.remove(file_path)

        # Remove the entry from renaming_operations after successful renaming
        del renaming_operations[file_id]
