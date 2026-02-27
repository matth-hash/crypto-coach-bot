from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from database import get_user
from psychology_engine import get_psychology_report, analyze_trading_behavior

router = Router()

@router.message(Command("psycho"))
async def cmd_psychology(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "en"

    loading = {
        "fr": "🧠 Génération de ton rapport psychologique...",
        "en": "🧠 Generating your psychological report...",
        "es": "🧠 Generando tu informe psicológico...",
        "pt": "🧠 Gerando seu relatório psicológico...",
    }
    msg = await message.answer(loading.get(lang, loading["en"]))

    report = await get_psychology_report(user_id, lang)
    await msg.edit_text(report, parse_mode="Markdown")

@router.message(Command("check"))
async def cmd_check(message: Message):
    """Vérifie les alertes comportementales en temps réel."""
    user_id = message.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "en"

    alerts = await analyze_trading_behavior(user_id, lang)

    if not alerts:
        ok_messages = {
            "fr": "✅ Tout est bon ! Aucune alerte comportementale détectée.",
            "en": "✅ All good! No behavioral alerts detected.",
            "es": "✅ ¡Todo bien! No se detectaron alertas conductuales.",
            "pt": "✅ Tudo certo! Nenhum alerta comportamental detectado.",
        }
        await message.answer(ok_messages.get(lang, ok_messages["en"]))
        return

    for alert in alerts:
        await message.answer(alert, parse_mode="Markdown")