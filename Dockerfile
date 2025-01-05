# Dockerfile for Telegram Media Bot

# Use the official Python image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot code
COPY . .

# Expose the port for Prometheus metrics
EXPOSE 8000

# Command to run the bot
CMD ["python", "telegram_media_bot.py"]
