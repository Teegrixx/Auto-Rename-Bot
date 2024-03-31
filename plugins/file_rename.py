from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InputMediaDocument, Message 
from PIL import Image
from datetime import datetime
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from helper.utils import progress_for_pyrogram, humanbytes, convert
from helper.database import madflixbotz
from config import Config
import os
import time
import re

renaming_operations = {}

# Pattern 1: S01E02 or S01EP02
pattern1 = re.compile(r'S(\d+)(?:E|EP)(\d+)')
# Pattern 2: S01 E02 or S01 EP02 or S01 - E01 or S01 - EP02
pattern2 = re.compile(r'S(\d+)\s*(?:E|EP|-\s*EP)(\d+)')
# Pattern 3: Episode Number After "E" or "EP"
pattern3 = re.compile(r'(?:[([<{]?\s*(?:E|EP)\s*(\d+)\s*[)\]>}]?)')
# Pattern 3_2: episode number after - [hyphen]
pattern3_2 = re.compile(r'(?:\s*-\s*(\d+)\s*)')
# Pattern 4: S2 09 ex.
pattern4 = re.compile(r'S(\d+)[^\d]*(\d+)', re.IGNORECASE)
# Pattern X: Standalone Episode Number
patternX = re.compile(r'(\d+)')
#QUALITY PATTERNS 
# Pattern 5: 3-4 digits before 'p' as quality
pattern5 = re.compile(r'\b(?:.*?(\d{3,4}[^\dp]*p).*?|.*?(\d{3,4}p))\b', re.IGNORECASE)
# Pattern 6: Find 4k in brackets or parentheses
pattern6 = re.compile(r'[([<{]?\s*4k\s*[)\]>}]?', re.IGNORECASE)
# Pattern 7: Find 2k in brackets or parentheses
pattern7 = re.compile(r'[([<{]?\s*2k\s*[)\]>}]?', re.IGNORECASE)
# Pattern 8: Find HdRip without spaces
pattern8 = re.compile(r'[([<{]?\s*HdRip\s*[)\]>}]?|\bHdRip\b', re.IGNORECASE)
# Pattern 9: Find 4kX264 in brackets or parentheses
pattern9 = re.compile(r'[([<{]?\s*4kX264\s*[)\]>}]?', re.IGNORECASE)
# Pattern 10: Find 4kx265 in brackets or parentheses
pattern10 = re.compile(r'[([<{]?\s*4kx265\s*[)\]>}]?', re.IGNORECASE)

def extract_quality(filename):
    # Try Quality Patterns
    match5 = re.search(pattern5, filename)
    if match5:
        print("Matched Pattern 5")
        quality5 = match5.group(1) or match5.group(2)  # Extracted quality from both patterns
        print(f"Quality: {quality5}")
        return quality5

    match6 = re.search(pattern6, filename)
    if match6:
        print("Matched Pattern 6")
        quality6 = "4k"
        print(f"Quality: {quality6}")
        return quality6

    match7 = re.search(pattern7, filename)
    if match7:
        print("Matched Pattern 7")
        quality7 = "2k"
        print(f"Quality: {quality7}")
        return quality7

    match8 = re.search(pattern8, filename)
    if match8:
        print("Matched Pattern 8")
        quality8 = "HdRip"
        print(f"Quality: {quality8}")
        return quality8

    match9 = re.search(pattern9, filename)
    if match9:
        print("Matched Pattern 9")
        quality9 = "4kX264"
        print(f"Quality: {quality9}")
        return quality9

    match10 = re.search(pattern10, filename)
    if match10:
        print("Matched Pattern 10")
        quality10 = "4kx265"
        print(f"Quality: {quality10}")
        return quality10    

    # Return "Unknown" if no pattern matches
    unknown_quality = "Unknown"
    print(f"Quality: {unknown_quality}")
    return unknown_quality
    

def extract_episode_number(filename):    
    # Try Pattern 1
    match = re.search(pattern1, filename)
    if match:
        print("Matched Pattern 1")
        return match.group(2)  # Extracted episode number
    
    # Try Pattern 2
    match = re.search(pattern2, filename)
    if match:
        print("Matched Pattern 2")
        return match.group(2)  # Extracted episode number

    # Try Pattern 3
    match = re.search(pattern3, filename)
    if match:
        print("Matched Pattern 3")
        return match.group(1)  # Extracted episode number

    # Try Pattern 3_2
    match = re.search(pattern3_2, filename)
    if match:
        print("Matched Pattern 3_2")
        return match.group(1)  # Extracted episode number
        
    # Try Pattern 4
    match = re.search(pattern4, filename)
    if match:
        print("Matched Pattern 4")
        return match.group(2)  # Extracted episode number

    # Try Pattern X
    match = re.search(patternX, filename)
    if match:
        print("Matched Pattern X")
        return match.group(1)  # Extracted episode number
        
    # Return None if no pattern matches
    return None

# Example Usage:
filename = "Naruto Shippuden S01 - EP07 - 1080p [Dual Audio] @teegrixx.mkv"
episode_number = extract_episode_number(filename)
print(f"Extracted Episode Number: {episode_number}")

# Inside the handler for file uploads
@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def download_file(session, url, file_path, progress_callback):
    async with session.get(url) as response:
        if response.status == 200:
            with open(file_path, 'wb') as f:
                content_length = int(response.headers.get('content-length')) if 'content-length' in response.headers else None
                downloaded_bytes = 0
                async for chunk in response.content.iter_any():
                    f.write(chunk)
                    downloaded_bytes += len(chunk)
                    if progress_callback:
                        await progress_callback(downloaded_bytes, content_length)
            return True
        else:
            print(f"Failed to download {url}: {response.status}")
            return False

async def upload_file(session, file_path, destination_url, progress_callback):
    data = aiohttp.FormData()
    data.add_field('file', open(file_path, 'rb'))
    async with session.post(destination_url, data=data) as response:
        if response.status == 200:
            print(f"File uploaded successfully to {destination_url}")
        else:
            print(f"Failed to upload {file_path} to {destination_url}: {response.status}")

async def process_file(session, url, destination_url, progress_callback):
    file_name = os.path.basename(url)
    download_success = await download_file(session, url, file_name, progress_callback)
    if download_success:
        await upload_file(session, file_name, destination_url, progress_callback)
        os.remove(file_name)

async def auto_rename_files(client, message):
    # Your existing code...

    async with aiohttp.ClientSession() as session:
        download_msg = await message.reply_text(text="Trying To Download.....")

        async def download_progress_callback(downloaded_bytes, total_bytes):
            if total_bytes:
                progress_percentage = int((downloaded_bytes / total_bytes) * 100)
                await download_msg.edit(f"Download Progress: {progress_percentage}%")

        try:
            await asyncio.create_task(
                download_file(session, file_url, file_path, download_progress_callback)
            )
        except Exception as e:
            del renaming_operations[file_id]
            return await download_msg.edit(f"Error downloading file: {e}")

        upload_msg = await download_msg.edit("Trying To Uploading.....")
        
        async def upload_progress_callback(transferred_bytes, total_bytes):
            if total_bytes:
                progress_percentage = int((transferred_bytes / total_bytes) * 100)
                await upload_msg.edit(f"Upload Progress: {progress_percentage}%")

        try:
            await asyncio.create_task(
                upload_file(session, file_path, upload_url, upload_progress_callback)
            )
        except Exception as e:
            os.remove(file_path)
            # Mark the file as ignored
            del renaming_operations[file_id]
            return await upload_msg.edit(f"Error uploading file: {e}")

        await download_msg.delete()
        await upload_msg.delete()

        # Remove the entry from renaming_operations after successful renaming
        del renaming_operations[file_id]



# Jishu Developer 
# Don't Remove Credit 🥺
# Telegram Channel @Madflix_Bots
# Developer @JishuDeveloper
