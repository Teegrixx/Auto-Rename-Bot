from datetime import datetime
from pytz import timezone
from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from config import Config
from aiohttp import web
from route import web_server
import aiofiles

class Bot(Client):

    def __init__(self):
        super().__init__(
            name="renamer",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            workers=200,
            plugins={"root": "plugins"},
            sleep_threshold=15,
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.mention = me.mention
        self.username = me.username  
        self.uptime = Config.BOT_UPTIME     
        if Config.WEBHOOK:
            app = web.AppRunner(await web_server())
            await app.setup()       
            await web.TCPSite(app, "0.0.0.0", 8080).start()     
        print(f"{me.first_name} Is Started.....✨️")
        for id in Config.ADMIN:
            try: await self.send_message(Config.LOG_CHANNEL, f"**{me.first_name}  Is Started.....✨️**")                                
            except: pass
        if Config.LOG_CHANNEL:
            try:
                curr = datetime.now(timezone("Asia/Kolkata"))
                date = curr.strftime('%d %B, %Y')
                time = curr.strftime('%I:%M:%S %p')
                await self.send_message(Config.LOG_CHANNEL, f"**{me.mention} Is Restarted !!**\n\n📅 Date : `{date}`\n⏰ Time : `{time}`\n🌐 Timezone : `Asia/Kolkata`\n\n🉐 Version : `v{__version__} (Layer {layer})`</b>")                                
            except:
                print("Please Make This Is Admin In Your Log Channel")
    
    async def download_file(self, message, file_path, progress_msg):
        try:
            async with aiofiles.open(file_path, "wb") as file:
                await self.download_media(
                    message=message,
                    file=file,
                    progress=progress_for_pyrogram,
                    progress_args=("Download Started....", progress_msg, time.time())
                )
            return True
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return False

    async def upload_file(self, chat_id, file_path, caption, media_type, duration, progress_msg):
        try:
            async with aiofiles.open(file_path, "rb") as file:
                if media_type == "document":
                    await self.send_document(
                        chat_id,
                        document=file,
                        caption=caption,
                        progress=progress_for_pyrogram,
                        progress_args=("Upload Started.....", progress_msg, time.time())
                    )
                elif media_type == "video":
                    await self.send_video(
                        chat_id,
                        video=file,
                        caption=caption,
                        duration=duration,
                        progress=progress_for_pyrogram,
                        progress_args=("Upload Started.....", progress_msg, time.time())
                    )
                elif media_type == "audio":
                    await self.send_audio(
                        chat_id,
                        audio=file,
                        caption=caption,
                        duration=duration,
                        progress=progress_for_pyrogram,
                        progress_args=("Upload Started.....", progress_msg, time.time())
                    )
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return False
        return True

Bot().run()
