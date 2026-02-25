import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import TELEGRAM_TOKEN
from bot.handlers import router
from database import init_db

logging.basicConfig(level=logging.INFO)

async def main():
    # Initialiser la base de données
    await init_db()

    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    print("🚀 CryptoCoach Bot démarré avec base de données !")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())