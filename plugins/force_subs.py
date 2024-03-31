from pyrogram import Client, filters, enums 
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import UserNotParticipant
from config import Config
from helper.database import madflixbotz

async def not_subscribed(_, client, message):
    await madflixbotz.add_user(client, message)
    if not Config.FORCE_SUB or not Config.FORCE_SUB_2:
        return False
    try:             
        user_channel_1 = await client.get_chat_member(Config.FORCE_SUB, message.from_user.id) 
        user_channel_2 = await client.get_chat_member(Config.FORCE_SUB_2, message.from_user.id)
        if user_channel_1.status == enums.ChatMemberStatus.BANNED or user_channel_2.status == enums.ChatMemberStatus.BANNED:
            return True 
        else:
            return False                
    except UserNotParticipant:
        pass
    return True


@Client.on_message(filters.private & filters.create(not_subscribed))
async def forces_sub(client, message):
    buttons = [
        [InlineKeyboardButton(text="🔺 Update Channel 1 🔺", url=f"https://t.me/{Config.FORCE_SUB}")],
        [InlineKeyboardButton(text="🔺 Update Channel 2 🔺", url=f"https://t.me/{Config.FORCE_SUB_2}")]
    ]
    text = "<b>Hello Dear \n\nYou Need To Join In My Channels To Use Me\n\nKindly Please Join Channel 1 and Channel 2</b>"
    try:
        user_channel_1 = await client.get_chat_member(Config.FORCE_SUB, message.from_user.id)    
        user_channel_2 = await client.get_chat_member(Config.FORCE_SUB_2, message.from_user.id)    
        if user_channel_1.status == enums.ChatMemberStatus.BANNED or user_channel_2.status == enums.ChatMemberStatus.BANNED:                                   
            return await client.send_message(message.from_user.id, text="Sorry You Are Banned To Use Me")  
    except UserNotParticipant:                       
        return await message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))
    return await message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))
