import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import yt_dlp
import re
import os
import uuid
import asyncio
from telegram_media_bot.social_media_monitor import monitor_inbox

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

user_codes = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_code = str(uuid.uuid4())
    user_codes[user_id] = user_code
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Your unique code is: {user_code}. Send this code along with links to your social media inboxes.")

async def download_media(url):
    ydl_opts = {
        'outtmpl': 'downloaded_media/%(title)s.%(ext)s',
        'format': 'best',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url_pattern = re.compile(r'https?://\S+')
    message_text = update.message.text
    if url_pattern.search(message_text):
        url = url_pattern.search(message_text).group(0)
        try:
            downloaded_file = await download_media(url)
            await context.bot.send_document(chat_id=update.effective_chat.id, document=open(downloaded_file, 'rb'))
            os.remove(downloaded_file)
        except Exception as e:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error downloading media: {e}")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please send a valid URL.")

async def check_social_media_inboxes(context: ContextTypes.DEFAULT_TYPE):
    while True:
        for user_id, user_code in user_codes.items():
            messages = monitor_inbox(user_code)
            for url in messages:
                try:
                    downloaded_file = await download_media(url)
                    await context.bot.send_document(chat_id=user_id, document=open(downloaded_file, 'rb'))
                    os.remove(downloaded_file)
                except Exception as e:
                    await context.bot.send_message(chat_id=user_id, text=f"Error downloading media from social media: {e}")
        await asyncio.sleep(60) # Check every 60 seconds

if __name__ == '__main__':
    application = ApplicationBuilder().token('7690911140:AAGGSP8It_Upn7wQR1VFTS2fomEtK5CxdJA').build()
    
    start_handler = CommandHandler('start', start)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    application.add_handler(start_handler)
    application.add_handler(message_handler)
    
    application.job_queue.run_repeating(check_social_media_inboxes, interval=60, first=1)
    
    application.run_polling()
