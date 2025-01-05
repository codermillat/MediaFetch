# MediaFetch Telegram Bot

This is a Telegram bot that allows users to download videos from various platforms such as YouTube, TikTok, Instagram, and Vimeo. The bot supports adaptive compression for large files and includes metrics monitoring using Prometheus.

## Features

- Video downloading from multiple platforms.
- Adaptive compression for files exceeding 2GB.
- Retry mechanism for failed downloads.
- Metrics monitoring with Prometheus.
- Integration with RabbitMQ for task management.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/codermillat/MediaFetch.git
   ```

2. Navigate to the project directory:
   ```bash
   cd MediaFetch
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the bot using Docker:
   ```bash
   docker-compose up --build
   ```

## Usage

- Start the bot and use the `/start` command to get started.
- Send a video link to download.

## License

This project is licensed under the MIT License.
