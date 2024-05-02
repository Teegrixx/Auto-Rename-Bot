from datetime import datetime
from pytz import timezone
from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from config import Config
from aiohttp import web
from route import web_server

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
        try:
            await super().start()
            me = await self.get_me()
            self.mention = me.mention
            self.username = me.username  
            self.uptime = Config.BOT_UPTIME     
            if Config.WEBHOOK:
                app = web.Application()
                app.add_routes(web_server())  # Add routes to the app
                app_runner = web.AppRunner(app)
                await app_runner.setup()
                await web.TCPSite(app_runner, "0.0.0.0", 8080).start()     
     
            print(f"{me.first_name} Is Started.....✨️")
            for id in Config.ADMIN:
                try: await self.send_message(Config.LOG_CHANNEL, f"**{me.first_name}  Is Started.....✨️**")                                
                except Exception as e:
                    print(f"Failed to send start message to admin: {e}")
            if Config.LOG_CHANNEL:
                try:
                    curr = datetime.now(timezone("Asia/Kolkata"))
                    date = curr.strftime('%d %B, %Y')
                    time = curr.strftime('%I:%M:%S %p')
                    await self.send_message(Config.LOG_CHANNEL, f"**{me.mention} Is Restarted !!**\n\n📅 Date : `{date}`\n⏰ Time : `{time}`\n🌐 Timezone : `Asia/Kolkata`\n\n🉐 Version : `v{__version__} (Layer {layer})`</b>")                                
                except Exception as e:
                    print(f"Failed to send restart message to log channel: {e}")
        except Exception as e:
            print(f"An error occurred while starting the bot: {e}")

if __name__ == "__main__":
    Bot().run()
 