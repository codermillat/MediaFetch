import logging
import os
import pika
from prometheus_client import start_http_server, Counter
from tenacity import retry, stop_after_attempt, wait_exponential
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler
import telegram.ext.filters as filters

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# Metrics
TOTAL_REQUESTS = Counter('total_requests', 'Total video requests received')
SUCCESSFUL_DELIVERIES = Counter('successful_deliveries', 'Total successful video deliveries')
FAILED_REQUESTS = Counter('failed_requests', 'Total failed video requests')

def setup_rabbitmq():
    """Set up RabbitMQ connection and declare queues."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='download_tasks', durable=True)
    channel.queue_declare(queue='dead_letter_queue', durable=True)
    return connection, channel

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def download_video(link, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(link, download=True)
        return ydl.prepare_filename(info_dict)

async def download_media(update: Update, context: CallbackContext, channel) -> None:
    """Download media from a provided link."""
    link = update.message.text
    TOTAL_REQUESTS.inc()  # Increment total requests counter
    await update.message.reply_text(f'Downloading media from {link}...')
    
    ydl_opts = {
        'format': 'best',
        'outtmpl': '/Users/millat/Desktop/MediaFetch/downloads/%(title)s.%(ext)s',
    }

    try:
        filename = download_video(link, ydl_opts)
        SUCCESSFUL_DELIVERIES.inc()  # Increment successful deliveries counter

        # Get info_dict for compression logic
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(link, download=False)

        # Check file size and compress if necessary
        if os.path.getsize(filename) > 2 * 1024 * 1024 * 1024:  # 2GB
            await update.message.reply_text('Compressing video...')
            compressed_filename = f'/Users/millat/Desktop/MediaFetch/downloads/compressed_{info_dict["title"]}.mp4'
            command = f'ffmpeg -i "{filename}" -vcodec libx264 -crf 23 "{compressed_filename}"'
            os.system(command)
            filename = compressed_filename

        await update.message.reply_document(document=open(filename, 'rb'))
        await update.message.reply_text(f'Media from {link} has been downloaded and sent!')
    except Exception as e:
        logger.error(f'Failed to download media from {link}: {e}')
        FAILED_REQUESTS.inc()  # Increment failed requests counter
        await update.message.reply_text(f'Failed to download media from {link}. Please try again later.')
        # Send failed task to dead letter queue
        channel.basic_publish(exchange='', routing_key='dead_letter_queue', body=link)

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    update.message.reply_text('Welcome to the Media Fetch Bot! Use /help to see available commands.')

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('Use /start to get started and send a video link to download.')

def main() -> None:
    """Start the bot and metrics server."""
    # Start Prometheus metrics server
    start_http_server(8000)  # Expose metrics on port 8000

    # Set up RabbitMQ
    connection, channel = setup_rabbitmq()

    # Create the Updater and pass it your bot's token.
    application = Application.builder().token("YOUR_BOT_TOKEN").build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_media))

    # Start the Bot
    application.run_polling()

    # Close RabbitMQ connection on exit
    connection.close()

if __name__ == '__main__':
    main()
