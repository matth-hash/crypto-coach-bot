from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import detect_language
from locales.translations import (
    TEXTS, LEVEL_BUTTONS, STYLE_BUTTONS, GOAL_BUTTONS
)
from ai_coach import get_coaching_response
from database import (
    get_user, create_user, update_user_profile,
    get_conversation_history, save_message,
    clear_conversation_history, update_xp
)

router = Router()

class ProfileSetup(StatesGroup):
    waiting_level = State()
    waiting_style = State()
    waiting_goal = State()
    coaching = State()

def make_keyboard(buttons: list, prefix: str):
    builder = InlineKeyboardBuilder()
    for btn in buttons:
        builder.button(text=btn, callback_data=f"{prefix}:{btn}")
    builder.adjust(1)
    return builder.as_markup()

# ─── /start ─────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    lang = detect_language(message.from_user.language_code)

    # Vérifier si l'utilisateur existe déjà
    existing_user = await get_user(user_id)

    if existing_user and existing_user.get("level"):
        # Utilisateur connu — on le reconnecte
        lang = existing_user["language"]
        await state.update_data(language=lang)
        await state.set_state(ProfileSetup.coaching)

        returning_messages = {
            "fr": f"👋 Content de te revoir ! Ton profil est intact. Pose-moi une question !",
            "en": f"👋 Welcome back! Your profile is intact. Ask me a question!",
            "es": f"👋 ¡Bienvenido de nuevo! Tu perfil está intacto. ¡Hazme una pregunta!",
            "pt": f"👋 Bem-vindo de volta! Seu perfil está intacto. Faça-me uma pergunta!",
        }
        await message.answer(returning_messages[lang])
        return

    # Nouvel utilisateur
    await create_user(user_id, username, lang)
    await state.update_data(language=lang)
    await message.answer(TEXTS["welcome"][lang])
    await message.answer(
        TEXTS["question_level"][lang],
        reply_markup=make_keyboard(LEVEL_BUTTONS[lang], "level")
    )
    await state.set_state(ProfileSetup.waiting_level)

# ─── /reset ─────────────────────────────────────────────────────

@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "en"

    await clear_conversation_history(user_id)
    await update_user_profile(user_id, level=None, trading_style=None, goal=None)
    await state.clear()

    reset_messages = {
        "fr": "🔄 Profil réinitialisé. Envoie /start pour recommencer.",
        "en": "🔄 Profile reset. Send /start to start over.",
        "es": "🔄 Perfil reiniciado. Envía /start para empezar de nuevo.",
        "pt": "🔄 Perfil redefinido. Envie /start para recomeçar.",
    }
    await message.answer(reset_messages[lang])

# ─── /profil ────────────────────────────────────────────────────

@router.message(Command("profil"))
async def cmd_profile(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user:
        await message.answer("Envoie /start pour créer ton profil.")
        return

    lang = user["language"]

    profile_texts = {
        "fr": (
            f"👤 *Ton profil*\n\n"
            f"📊 Niveau : {user.get('level', 'Non défini')}\n"
            f"⚡ Style : {user.get('trading_style', 'Non défini')}\n"
            f"🎯 Objectif : {user.get('goal', 'Non défini')}\n"
            f"⭐ XP : {user.get('xp', 0)} points\n"
        ),
        "en": (
            f"👤 *Your profile*\n\n"
            f"📊 Level: {user.get('level', 'Not set')}\n"
            f"⚡ Style: {user.get('trading_style', 'Not set')}\n"
            f"🎯 Goal: {user.get('goal', 'Not set')}\n"
            f"⭐ XP: {user.get('xp', 0)} points\n"
        ),
        "es": (
            f"👤 *Tu perfil*\n\n"
            f"📊 Nivel: {user.get('level', 'No definido')}\n"
            f"⚡ Estilo: {user.get('trading_style', 'No definido')}\n"
            f"🎯 Objetivo: {user.get('goal', 'No definido')}\n"
            f"⭐ XP: {user.get('xp', 0)} puntos\n"
        ),
        "pt": (
            f"👤 *Seu perfil*\n\n"
            f"📊 Nível: {user.get('level', 'Não definido')}\n"
            f"⚡ Estilo: {user.get('trading_style', 'Não definido')}\n"
            f"🎯 Objetivo: {user.get('goal', 'Não definido')}\n"
            f"⭐ XP: {user.get('xp', 0)} pontos\n"
        ),
    }

    await message.answer(profile_texts[lang], parse_mode="Markdown")

# ─── Étapes du profil ────────────────────────────────────────────

@router.callback_query(ProfileSetup.waiting_level)
async def process_level(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    user_id = callback.from_user.id

    level = callback.data.split(":", 1)[1]
    await update_user_profile(user_id, level=level)

    await callback.message.edit_reply_markup()
    await callback.message.answer(
        TEXTS["question_style"][lang],
        reply_markup=make_keyboard(STYLE_BUTTONS[lang], "style")
    )
    await state.set_state(ProfileSetup.waiting_style)
    await callback.answer()

@router.callback_query(ProfileSetup.waiting_style)
async def process_style(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    user_id = callback.from_user.id

    style = callback.data.split(":", 1)[1]
    await update_user_profile(user_id, trading_style=style)

    await callback.message.edit_reply_markup()
    await callback.message.answer(
        TEXTS["question_goal"][lang],
        reply_markup=make_keyboard(GOAL_BUTTONS[lang], "goal")
    )
    await state.set_state(ProfileSetup.waiting_goal)
    await callback.answer()

@router.callback_query(ProfileSetup.waiting_goal)
async def process_goal(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    user_id = callback.from_user.id

    goal = callback.data.split(":", 1)[1]
    await update_user_profile(user_id, goal=goal)

    await callback.message.edit_reply_markup()
    await callback.message.answer(TEXTS["profile_complete"][lang])

    thinking_msg = await callback.message.answer(TEXTS["thinking"][lang])

    user = await get_user(user_id)
    intro_messages = {
        "fr": "Mon profil est configuré. Génère un message de bienvenue personnalisé et donne-moi un premier conseil adapté.",
        "en": "My profile is set up. Generate a personalized welcome and give me a first adapted tip.",
        "es": "Mi perfil está configurado. Genera una bienvenida personalizada y dame un primer consejo adaptado.",
        "pt": "Meu perfil está configurado. Gere uma boas-vindas personalizada e me dê uma primeira dica adaptada.",
    }

    response = await get_coaching_response(
        intro_messages[lang], lang, user, []
    )

    # Sauvegarder en base
    await save_message(user_id, "user", intro_messages[lang])
    await save_message(user_id, "assistant", response)
    await update_xp(user_id, 20)  # +20 XP pour avoir complété le profil

    await thinking_msg.delete()
    await callback.message.answer(response)
    await callback.message.answer(TEXTS["ask_question"][lang])
    await state.set_state(ProfileSetup.coaching)
    await callback.answer()

# ─── Coaching principal ──────────────────────────────────────────

@router.message(ProfileSetup.coaching)
async def handle_coaching_message(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    user_id = message.from_user.id

    thinking_msg = await message.answer(TEXTS["thinking"][lang])

    user = await get_user(user_id)
    if user:
        lang = user["language"]

    history = await get_conversation_history(user_id)

    response = await get_coaching_response(
        message.text, lang, user or {}, history
    )

    # Sauvegarder en base
    await save_message(user_id, "user", message.text)
    await save_message(user_id, "assistant", response)
    await update_xp(user_id, 5)  # +5 XP par message# Streak et badge premier message
    streak, badge_msg = await update_streak(user_id, lang)
    if badge_msg:
        await message.answer(badge_msg, parse_mode="Markdown")

    # Badge premier message
    from gamification import check_and_award_badge
    first_msg_badge = await check_and_award_badge(user_id, "first_message", lang)
    if first_msg_badge:
        await message.answer(first_msg_badge, parse_mode="Markdown")

    await thinking_msg.delete()
    await message.answer(response)