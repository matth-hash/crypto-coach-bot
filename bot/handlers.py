from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import detect_language
from locales.translations import (
    TEXTS, LEVEL_BUTTONS, STYLE_BUTTONS, GOAL_BUTTONS
)
from ai_coach import get_coaching_response

router = Router()

# États du profil utilisateur
class ProfileSetup(StatesGroup):
    waiting_level = State()
    waiting_style = State()
    waiting_goal = State()
    coaching = State()

# Stockage simple en mémoire (on ajoutera une DB plus tard)
user_profiles = {}
conversation_histories = {}

def make_keyboard(buttons: list, prefix: str):
    builder = InlineKeyboardBuilder()
    for btn in buttons:
        builder.button(text=btn, callback_data=f"{prefix}:{btn}")
    builder.adjust(1)
    return builder.as_markup()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    lang = detect_language(message.from_user.language_code)
    user_id = message.from_user.id

    # Initialiser le profil
    user_profiles[user_id] = {"language": lang}
    conversation_histories[user_id] = []

    await state.update_data(language=lang)

    # Message de bienvenue
    await message.answer(TEXTS["welcome"][lang])

    # Question niveau
    await message.answer(
        TEXTS["question_level"][lang],
        reply_markup=make_keyboard(LEVEL_BUTTONS[lang], "level")
    )
    await state.set_state(ProfileSetup.waiting_level)

@router.callback_query(ProfileSetup.waiting_level)
async def process_level(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    user_id = callback.from_user.id

    level = callback.data.split(":", 1)[1]
    user_profiles[user_id]["level"] = level

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
    user_profiles[user_id]["style"] = style

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
    user_profiles[user_id]["goal"] = goal

    await callback.message.edit_reply_markup()
    await callback.message.answer(TEXTS["profile_complete"][lang])

    # Premier message de coaching personnalisé
    thinking_msg = await callback.message.answer(TEXTS["thinking"][lang])

    profile = user_profiles[user_id]
    intro_messages = {
        "fr": f"Mon profil est maintenant configuré. Génère-moi un message de bienvenue personnalisé et donne-moi un premier conseil adapté à mon niveau et mon style.",
        "en": f"My profile is now set up. Generate a personalized welcome message and give me a first tip adapted to my level and style.",
        "es": f"Mi perfil está ahora configurado. Genera un mensaje de bienvenida personalizado y dame un primer consejo adaptado a mi nivel y estilo.",
        "pt": f"Meu perfil está configurado. Gere uma mensagem de boas-vindas personalizada e me dê uma primeira dica adaptada ao meu nível e estilo.",
    }

    response = await get_coaching_response(
        intro_messages[lang],
        lang,
        profile,
        []
    )

    await thinking_msg.delete()
    await callback.message.answer(response)
    await callback.message.answer(TEXTS["ask_question"][lang])

    await state.set_state(ProfileSetup.coaching)
    await callback.answer()

@router.message(ProfileSetup.coaching)
async def handle_coaching_message(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "en")
    user_id = message.from_user.id

    thinking_msg = await message.answer(TEXTS["thinking"][lang])

    profile = user_profiles.get(user_id, {"language": lang})
    history = conversation_histories.get(user_id, [])

    response = await get_coaching_response(
        message.text,
        lang,
        profile,
        history
    )

    # Mettre à jour l'historique (garder les 10 derniers échanges)
    history.append({"role": "user", "content": message.text})
    history.append({"role": "assistant", "content": response})
    conversation_histories[user_id] = history[-20:]

    await thinking_msg.delete()
    await message.answer(response)