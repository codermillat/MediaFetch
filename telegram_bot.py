import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import yt_dlp

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    unique_code = generate_unique_code(user.id)
    update.message.reply_text(f'Hi {user.first_name}! Your unique code is {unique_code}. Please use this code in your social media inboxes along with the media link.')

def generate_unique_code(user_id: int) -> str:
    """Generate a unique code for the user."""
    # Placeholder for unique code generation logic
    return f"code_{user_id}"

def process_telegram_links(update: Update, context: CallbackContext) -> None:
    """Process links sent directly through Telegram."""
    link = update.message.text
    try:
        media_path = download_media(link)
        with open(media_path, 'rb') as media_file:
            update.message.reply_document(media_file)
    except Exception as e:
        logger.error(f"Failed to process link {link}: {e}")
        update.message.reply_text(f"Failed to download media from {link}. Please try again later.")

def download_media(link: str) -> str:
    """Download media from the provided link using yt-dlp."""
    ydl_opts = {
        'outtmpl': '%(title)s.%(ext)s',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(link, download=True)
        return ydl.prepare_filename(info_dict)

def main() -> None:
    """Start the bot."""
    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))

    # on noncommand i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, process_telegram_links))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()

if __name__ == '__main__':
    main()
