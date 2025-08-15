web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --keep-alive 5
worker: python worker.py
telegram: python robust_telegram_bot.py
