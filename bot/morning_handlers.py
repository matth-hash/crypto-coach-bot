from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_user, set_morning_time

router = Router()

# Créneaux horaires proposés (UTC)
MORNING_SLOTS = [
    "05:00", "05:30", "06:00", "06:30",
    "07:00", "07:30", "08:00", "08:30",
    "09:00", "09:30", "10:00",
]

def morning_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    for slot in MORNING_SLOTS:
        builder.button(text=f"🕐 {slot} UTC", callback_data=f"morning_set:{slot}")
    builder.adjust(3)

    disable_labels = {
        "fr": "❌ Désactiver",
        "en": "❌ Disable",
        "es": "❌ Desactivar",
        "pt": "❌ Desativar",
    }
    builder.button(
        text=disable_labels.get(lang, disable_labels["fr"]),
        callback_data="morning_set:off"
    )
    builder.adjust(3)
    return builder.as_markup()

@router.message(Command("morning"))
async def cmd_morning(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "fr"

    current = user.get("morning_time") if user else None

    texts = {
        "fr": (
            f"🌅 *Brief Matinal*\n\n"
            f"Reçois chaque matin un résumé des marchés + un conseil personnalisé.\n\n"
            f"{'✅ Actuellement configuré à : ' + current + ' UTC' if current else '❌ Non activé'}\n\n"
            f"Choisis ton heure de réception _(heure UTC)_ :"
        ),
        "en": (
            f"🌅 *Morning Brief*\n\n"
            f"Receive every morning a market summary + personalized tip.\n\n"
            f"{'✅ Currently set at: ' + current + ' UTC' if current else '❌ Not enabled'}\n\n"
            f"Choose your delivery time _(UTC time)_ :"
        ),
        "es": (
            f"🌅 *Brief Matutino*\n\n"
            f"Recibe cada mañana un resumen de mercados + consejo personalizado.\n\n"
            f"{'✅ Configurado actualmente a las: ' + current + ' UTC' if current else '❌ No activado'}\n\n"
            f"Elige tu hora de recepción _(hora UTC)_ :"
        ),
        "pt": (
            f"🌅 *Brief Matinal*\n\n"
            f"Receba toda manhã um resumo dos mercados + dica personalizada.\n\n"
            f"{'✅ Atualmente configurado para: ' + current + ' UTC' if current else '❌ Não ativado'}\n\n"
            f"Escolha seu horário de recebimento _(horário UTC)_ :"
        ),
    }

    await message.answer(
        texts.get(lang, texts["fr"]),
        reply_markup=morning_keyboard(lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("morning_set:"))
async def cb_morning_set(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "fr"
    time_str = callback.data.split(":")[1]

    if time_str == "off":
        await set_morning_time(user_id, None)
        messages = {
            "fr": "❌ Brief matinal désactivé.",
            "en": "❌ Morning brief disabled.",
            "es": "❌ Brief matutino desactivado.",
            "pt": "❌ Brief matinal desativado.",
        }
    else:
        await set_morning_time(user_id, time_str)
        messages = {
            "fr": f"✅ Brief matinal activé à *{time_str} UTC* !\n\nChaque matin tu recevras les prix + un conseil personnalisé. 🌅",
            "en": f"✅ Morning brief set to *{time_str} UTC*!\n\nEvery morning you'll receive prices + a personalized tip. 🌅",
            "es": f"✅ Brief matutino activado a las *{time_str} UTC*!\n\nCada mañana recibirás los precios + un consejo personalizado. 🌅",
            "pt": f"✅ Brief matinal ativado às *{time_str} UTC*!\n\nCada manhã você receberá os preços + uma dica personalizada. 🌅",
        }

    await callback.message.edit_text(
        messages.get(lang, messages["fr"]),
        parse_mode="Markdown"
    )
    await callback.answer()
