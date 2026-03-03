# CryptoCoach Bot

A multilingual Telegram crypto trading coaching bot.

## Tech Stack
- Python 3.10+
- aiogram 3.4.1 (Telegram Bot API)
- pycoingecko (Market Data API)
- yfinance (Stock & Crypto Data)
- stripe (Payment Integration)
- Anthropic Claude AI (Coaching Engine)
- PostgreSQL (Database)
- ccxt (Exchange Integration)

## Features
- Multilingual support (FR, EN, ES, PT)
- Personalized trading coaching based on user profile
- Exchange connection (Binance, Bybit, KuCoin, OKX, Kraken, Bitget)
- Psychological bias detection
- Gamification (XP, Streaks, Badges)

## Project Structure
- `main.py`: Entry point
- `bot/`: Bot handlers and logic
  - `handlers.py`: Main command and coaching handlers
  - `exchange_handlers.py`: Exchange connection and trade fetching
  - `gamification_handlers.py`: Streaks and badges
- `ai_coach.py`: Claude AI integration
- `database.py`: PostgreSQL operations
- `exchange_manager.py`: CCXT wrapper
- `config.py`: Configuration and environment variables

## Environment Variables
- `TELEGRAM_TOKEN`: Telegram Bot API token
- `ANTHROPIC_API_KEY`: Anthropic API key
- `DATABASE_URL`: PostgreSQL connection string
