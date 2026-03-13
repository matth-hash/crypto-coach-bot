import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import TELEGRAM_TOKEN
from bot.handlers import router as main_router
from bot.exchange_handlers import router as exchange_router
from bot.psychology_handlers import router as psychology_router
from bot.gamification_handlers import router as gamification_router
from bot.payment_handlers import router as payment_router
from bot.help_handlers import router as help_router
from bot.callback_handlers import router as callback_router
from bot.lexique_handlers import router as lexique_router
from bot.morning_handlers import router as morning_router
from bot.alerts_handlers import router as alerts_router
from database import init_db
from scheduler import run_morning_briefs, run_price_alerts
from payments import start_webhook_server

logging.basicConfig(level=logging.INFO)

async def main():
    await init_db()

    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(exchange_router)
    dp.include_router(psychology_router)
    dp.include_router(gamification_router)
    dp.include_router(payment_router)
    dp.include_router(help_router)
    dp.include_router(lexique_router)
    dp.include_router(morning_router)
    dp.include_router(alerts_router)
    dp.include_router(callback_router)
    dp.include_router(main_router)

    # Jobs en arrière-plan
    asyncio.create_task(run_morning_briefs(bot))
    asyncio.create_task(run_price_alerts(bot))
    asyncio.create_task(start_webhook_server())

    print("🚀 TradeCoach Bot démarré !")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
