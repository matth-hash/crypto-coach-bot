import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import TELEGRAM_TOKEN
from bot.handlers import router as main_router
from bot.exchange_handlers import router as exchange_router
from bot.psychology_handlers import router as psychology_router
from bot.gamification_handlers import router as gamification_router
from database import init_db

logging.basicConfig(level=logging.INFO)

async def main():
    await init_db()

    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(exchange_router)
    dp.include_router(psychology_router)
    dp.include_router(gamification_router)
    dp.include_router(main_router)

    print("🚀 CryptoCoach Bot démarré !")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())