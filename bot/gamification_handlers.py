from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from database import get_user, update_xp
from gamification import (
    get_level_info, make_progress_bar,
    get_badges_list, update_streak,
    check_and_award_badge
)

router = Router()

@router.message(Command("niveau"))
@router.message(Command("level"))
async def cmd_level(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user:
        await message.answer("Envoie /start pour créer ton profil.")
        return

    lang = user["language"]
    xp = user.get("xp", 0)
    streak = user.get("streak_days", 0)

    level_info = get_level_info(xp, lang)
    progress_bar = make_progress_bar(level_info["progress"])
    badges = await get_badges_list(user_id, lang)

    badges_text = " ".join([b["icon"] for b in badges]) if badges else "—"

    next_level_texts = {
        "fr": f"Prochain niveau dans *{level_info['xp_to_next']} XP*",
        "en": f"Next level in *{level_info['xp_to_next']} XP*",
        "es": f"Siguiente nivel en *{level_info['xp_to_next']} XP*",
        "pt": f"Próximo nível em *{level_info['xp_to_next']} XP*",
    }

    max_level_texts = {
        "fr": "🏆 Niveau maximum atteint !",
        "en": "🏆 Maximum level reached!",
        "es": "🏆 ¡Nivel máximo alcanzado!",
        "pt": "🏆 Nível máximo atingido!",
    }

    next_text = (
        next_level_texts.get(lang, next_level_texts["en"])
        if level_info["xp_to_next"] > 0
        else max_level_texts.get(lang, max_level_texts["en"])
    )

    streak_fire = "🔥" * min(streak, 5) if streak > 0 else "—"

    profile_texts = {
        "fr": (
            f"⭐ *Ton niveau*\n\n"
            f"🎖️ {level_info['name']}\n"
            f"✨ XP : *{xp}*\n"
            f"📊 Progression : {progress_bar}\n"
            f"{next_text}\n\n"
            f"🔥 Streak : *{streak} jour(s)* {streak_fire}\n\n"
            f"🏆 Badges : {badges_text}"
        ),
        "en": (
            f"⭐ *Your level*\n\n"
            f"🎖️ {level_info['name']}\n"
            f"✨ XP: *{xp}*\n"
            f"📊 Progress: {progress_bar}\n"
            f"{next_text}\n\n"
            f"🔥 Streak: *{streak} day(s)* {streak_fire}\n\n"
            f"🏆 Badges: {badges_text}"
        ),
        "es": (
            f"⭐ *Tu nivel*\n\n"
            f"🎖️ {level_info['name']}\n"
            f"✨ XP: *{xp}*\n"
            f"📊 Progreso: {progress_bar}\n"
            f"{next_text}\n\n"
            f"🔥 Racha: *{streak} día(s)* {streak_fire}\n\n"
            f"🏆 Insignias: {badges_text}"
        ),
        "pt": (
            f"⭐ *Seu nível*\n\n"
            f"🎖️ {level_info['name']}\n"
            f"✨ XP: *{xp}*\n"
            f"📊 Progresso: {progress_bar}\n"
            f"{next_text}\n\n"
            f"🔥 Sequência: *{streak} dia(s)* {streak_fire}\n\n"
            f"🏆 Conquistas: {badges_text}"
        ),
    }

    await message.answer(
        profile_texts.get(lang, profile_texts["en"]),
        parse_mode="Markdown"
    )

@router.message(Command("badges"))
async def cmd_badges(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user:
        await message.answer("Envoie /start pour créer ton profil.")
        return

    lang = user["language"]
    badges = await get_badges_list(user_id, lang)

    if not badges:
        empty_texts = {
            "fr": "🏆 Tu n'as pas encore de badges.\n\nContinue à utiliser le bot pour en débloquer !",
            "en": "🏆 You don't have any badges yet.\n\nKeep using the bot to unlock some!",
            "es": "🏆 Aún no tienes insignias.\n\n¡Sigue usando el bot para desbloquear!",
            "pt": "🏆 Você ainda não tem conquistas.\n\nContinue usando o bot para desbloquear!",
        }
        await message.answer(empty_texts.get(lang, empty_texts["en"]))
        return

    headers = {
        "fr": f"🏆 *Tes badges ({len(badges)})*\n\n",
        "en": f"🏆 *Your badges ({len(badges)})*\n\n",
        "es": f"🏆 *Tus insignias ({len(badges)})*\n\n",
        "pt": f"🏆 *Suas conquistas ({len(badges)})*\n\n",
    }

    text = headers.get(lang, headers["en"])
    for badge in badges:
        text += f"{badge['icon']} {badge['name']}\n"

    await message.answer(text, parse_mode="Markdown")