from aiogram import Router, F
from aiogram.types import CallbackQuery

router = Router()

@router.callback_query(F.data == "show_premium")
async def cb_show_premium(callback: CallbackQuery):
    await callback.message.answer("/premium")
    await callback.answer()

@router.callback_query(F.data == "show_trades")
async def cb_show_trades(callback: CallbackQuery):
    await callback.message.answer("/trades")
    await callback.answer()