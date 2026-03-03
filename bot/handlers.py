from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.payment_handlers import check_free_limit

from config import detect_language
from locales.translations import (
    TEXTS, LEVEL_BUTTONS, STYLE_BUTTONS, GOAL_BUTTONS
)
from ai_coach import get_coaching_response
from database import (
    get_user, create_user, update_user_profile,
    get_conversation_history, save_message,
    clear_conversation_history, update_xp,
    save_exchange_connection, get_exchange_connection,
    get_user_exchanges, delete_exchange_connection
)
from exchange_manager import (
    test_connection, fetch_recent_trades,
    format_trades_for_analysis, SUPPORTED_EXCHANGES
)
from bot.gamification_handlers import update_streak

router = Router()

class ProfileSetup(StatesGroup):
    waiting_level = State()
    waiting_style = State()
    waiting_goal = State()
    coaching = State()

class ExchangeSetup(StatesGroup):
    choosing_exchange = State()
    waiting_api_key = State()
    waiting_api_secret = State()

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
            "es": f"👋 ¡Bienvenido de nuevo! Tu perfil está intacto. ¡Hazme una question!",
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
            f"⭐ XP: {user.get('xp', 0)} points\n"
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
    # Vérifier la limite freemium
    if not await check_free_limit(message, lang):
        return
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
    await update_xp(user_id, 5)  # +5 XP par message

    # Streak et badge
    streak, badge_msg = await update_streak(user_id, lang)
    if badge_msg:
        await message.answer(badge_msg, parse_mode="Markdown")

    from gamification import check_and_award_badge
    first_msg_badge = await check_and_award_badge(user_id, "first_message", lang)
    if first_msg_badge:
        await message.answer(first_msg_badge, parse_mode="Markdown")

    await thinking_msg.delete()
    await message.answer(response)

# ─── /exchange ───────────────────────────────────────────────────
EXCHANGE_API_INSTRUCTIONS = {
        "binance": {
            "fr": (
                "📖 *Comment créer tes clés API Binance :*\n\n"
                "1️⃣ Va sur binance.com → connecte-toi\n"
                "2️⃣ Clique sur ton profil (en haut à droite)\n"
                "3️⃣ Sélectionne *Gestion des API*\n"
                "4️⃣ Clique sur *Créer une API*\n"
                "5️⃣ Choisis *Clé API générée par le système*\n"
                "6️⃣ Donne un nom (ex: CryptoCoach)\n"
                "7️⃣ Active UNIQUEMENT ✅ *Lire*\n"
                "❌ Ne coche JAMAIS Retrait ou Trading\n\n"
                "🔗 Lien direct : myaccount.binance.com/fr/api-management"
            ),
            "en": (
                "📖 *How to create your Binance API keys:*\n\n"
                "1️⃣ Go to binance.com → log in\n"
                "2️⃣ Click your profile (top right)\n"
                "3️⃣ Select *API Management*\n"
                "4️⃣ Click *Create API*\n"
                "5️⃣ Choose *System generated API key*\n"
                "6️⃣ Give it a name (e.g. CryptoCoach)\n"
                "7️⃣ Enable ONLY ✅ *Read*\n"
                "❌ NEVER enable Withdrawal or Trading\n\n"
                "🔗 Direct link: myaccount.binance.com/en/api-management"
            ),
            "es": (
                "📖 *Cómo crear tus claves API de Binance:*\n\n"
                "1️⃣ Ve a binance.com → inicia sesión\n"
                "2️⃣ Haz clic en tu perfil (arriba a la derecha)\n"
                "3️⃣ Selecciona *Gestión de API*\n"
                "4️⃣ Haz clic en *Crear API*\n"
                "5️⃣ Elige *Clave API generada por el sistema*\n"
                "6️⃣ Dale un nombre (ej: CryptoCoach)\n"
                "7️⃣ Activa SOLO ✅ *Leer*\n"
                "❌ NUNCA actives Retiro o Trading\n\n"
                "🔗 Enlace directo: myaccount.binance.com/es/api-management"
            ),
            "pt": (
                "📖 *Como criar suas chaves API da Binance:*\n\n"
                "1️⃣ Vá para binance.com → faça login\n"
                "2️⃣ Clique no seu perfil (canto superior direito)\n"
                "3️⃣ Selecione *Gerenciamento de API*\n"
                "4️⃣ Clique em *Criar API*\n"
                "5️⃣ Escolha *Chave API gerada pelo sistema*\n"
                "6️⃣ Dê um nome (ex: CryptoCoach)\n"
                "7️⃣ Ative APENAS ✅ *Leitura*\n"
                "❌ NUNCA ative Saque ou Trading\n\n"
                "🔗 Link direto: myaccount.binance.com/pt/api-management"
            ),
        },
        "bybit": {
            "fr": (
                "📖 *Comment créer tes clés API Bybit :*\n\n"
                "1️⃣ Va sur bybit.com → connecte-toi\n"
                "2️⃣ Clique sur ton profil → *Paramètres du compte*\n"
                "3️⃣ Sélectionne *API* dans le menu\n"
                "4️⃣ Clique sur *Créer une nouvelle clé*\n"
                "5️⃣ Choisis *Clé API*\n"
                "6️⃣ Donne un nom (ex: CryptoCoach)\n"
                "7️⃣ Coche UNIQUEMENT ✅ *Lire*\n"
                "❌ Ne coche JAMAIS Retrait ou Trade\n\n"
                "🔗 Lien direct : bybit.com/app/user/api-management"
            ),
            "en": (
                "📖 *How to create your Bybit API keys:*\n\n"
                "1️⃣ Go to bybit.com → log in\n"
                "2️⃣ Click your profile → *Account Settings*\n"
                "3️⃣ Select *API* in the menu\n"
                "4️⃣ Click *Create New Key*\n"
                "5️⃣ Choose *API Key*\n"
                "6️⃣ Give it a name (e.g. CryptoCoach)\n"
                "7️⃣ Check ONLY ✅ *Read*\n"
                "❌ NEVER enable Withdrawal or Trade\n\n"
                "🔗 Direct link: bybit.com/app/user/api-management"
            ),
            "es": (
                "📖 *Cómo crear tus claves API de Bybit:*\n\n"
                "1️⃣ Ve a bybit.com → inicia sesión\n"
                "2️⃣ Haz clic en tu perfil → *Configuración de cuenta*\n"
                "3️⃣ Selecciona *API* en el menú\n"
                "4️⃣ Haz clic en *Crear nueva clave*\n"
                "5️⃣ Elige *Clave API*\n"
                "6️⃣ Dale un nombre (ej: CryptoCoach)\n"
                "7️⃣ Marca SOLO ✅ *Leer*\n"
                "❌ NUNCA actives Retiro o Trade\n\n"
                "🔗 Enlace directo: bybit.com/app/user/api-management"
            ),
            "pt": (
                "📖 *Como criar suas chaves API da Bybit:*\n\n"
                "1️⃣ Vá para bybit.com → faça login\n"
                "2️⃣ Clique no seu perfil → *Configurações da conta*\n"
                "3️⃣ Selecione *API* no menu\n"
                "4️⃣ Clique em *Criar nova chave*\n"
                "5️⃣ Escolha *Chave API*\n"
                "6️⃣ Dê um nome (ex: CryptoCoach)\n"
                "7️⃣ Marque APENAS ✅ *Leitura*\n"
                "❌ NUNCA ative Saque ou Trade\n\n"
                "🔗 Link direto: bybit.com/app/user/api-management"
            ),
        },
        "kucoin": {
            "fr": (
                "📖 *Comment créer tes clés API KuCoin :*\n\n"
                "1️⃣ Va sur kucoin.com → connecte-toi\n"
                "2️⃣ Clique sur ton profil → *Gestion des API*\n"
                "3️⃣ Clique sur *Créer une API*\n"
                "4️⃣ Donne un nom et un mot de passe API\n"
                "5️⃣ Coche UNIQUEMENT ✅ *Général* (lecture seule)\n"
                "❌ Ne coche JAMAIS Trade ou Transfert\n\n"
                "🔗 Lien direct : kucoin.com/account/api"
            ),
            "en": (
                "📖 *How to create your KuCoin API keys:*\n\n"
                "1️⃣ Go to kucoin.com → log in\n"
                "2️⃣ Click your profile → *API Management*\n"
                "3️⃣ Click *Create API*\n"
                "4️⃣ Set a name and API passphrase\n"
                "5️⃣ Check ONLY ✅ *General* (read only)\n"
                "❌ NEVER enable Trade or Transfer\n\n"
                "🔗 Direct link: kucoin.com/account/api"
            ),
            "es": (
                "📖 *Cómo crear tus claves API de KuCoin:*\n\n"
                "1️⃣ Ve a kucoin.com → inicia sesión\n"
                "2️⃣ Haz clic en tu perfil → *Gestión de API*\n"
                "3️⃣ Haz clic en *Crear API*\n"
                "4️⃣ Establece un nombre y contraseña API\n"
                "5️⃣ Marca SOLO ✅ *General* (solo lectura)\n"
                "❌ NUNCA actives Trade o Transferencia\n\n"
                "🔗 Enlace directo: kucoin.com/account/api"
            ),
            "pt": (
                "📖 *Como criar suas chaves API da KuCoin:*\n\n"
                "1️⃣ Vá para kucoin.com → faça login\n"
                "2️⃣ Clique no seu perfil → *Gerenciamento de API*\n"
                "3️⃣ Clique em *Criar API*\n"
                "4️⃣ Defina um nome e senha API\n"
                "5️⃣ Marque APENAS ✅ *Geral* (somente leitura)\n"
                "❌ NUNCA ative Trade ou Transferência\n\n"
                "🔗 Link direto: kucoin.com/account/api"
            ),
        },
        "okx": {
            "fr": (
                "📖 *Comment créer tes clés API OKX :*\n\n"
                "1️⃣ Va sur okx.com → connecte-toi\n"
                "2️⃣ Clique sur ton profil → *Paramètres*\n"
                "3️⃣ Sélectionne *API*\n"
                "4️⃣ Clique sur *Créer une clé API V5*\n"
                "5️⃣ Donne un nom et une passphrase\n"
                "6️⃣ Sélectionne UNIQUEMENT ✅ *Lecture*\n"
                "❌ Ne coche JAMAIS Trade ou Retrait\n\n"
                "🔗 Lien direct : okx.com/account/my-api"
            ),
            "en": (
                "📖 *How to create your OKX API keys:*\n\n"
                "1️⃣ Go to okx.com → log in\n"
                "2️⃣ Click your profile → *Settings*\n"
                "3️⃣ Select *API*\n"
                "4️⃣ Click *Create V5 API Key*\n"
                "5️⃣ Set a name and passphrase\n"
                "6️⃣ Select ONLY ✅ *Read*\n"
                "❌ NEVER enable Trade or Withdrawal\n\n"
                "🔗 Direct link: okx.com/account/my-api"
            ),
            "es": (
                "📖 *Cómo crear tus claves API de OKX:*\n\n"
                "1️⃣ Ve a okx.com → inicia sesión\n"
                "2️⃣ Haz clic en tu perfil → *Configuración*\n"
                "3️⃣ Selecciona *API*\n"
                "4️⃣ Haz clic en *Crear clave API V5*\n"
                "5️⃣ Establece un nombre y contraseña\n"
                "6️⃣ Selecciona SOLO ✅ *Lectura*\n"
                "❌ NUNCA actives Trade o Retiro\n\n"
                "🔗 Enlace directo: okx.com/account/my-api"
            ),
            "pt": (
                "📖 *Como criar suas chaves API da OKX:*\n\n"
                "1️⃣ Vá para okx.com → faça login\n"
                "2️⃣ Clique no seu perfil → *Configurações*\n"
                "3️⃣ Selecione *API*\n"
                "4️⃣ Clique em *Criar chave API V5*\n"
                "5️⃣ Defina um nome e senha\n"
                "6️⃣ Selecione APENAS ✅ *Leitura*\n"
                "❌ NUNCA ative Trade ou Saque\n\n"
                "🔗 Link direto: okx.com/account/my-api"
            ),
        },
        "kraken": {
            "fr": (
                "📖 *Comment créer tes clés API Kraken :*\n\n"
                "1️⃣ Va sur kraken.com → connecte-toi\n"
                "2️⃣ Clique sur ton nom → *Sécurité*\n"
                "3️⃣ Sélectionne *API*\n"
                "4️⃣ Clique sur *Ajouter une clé*\n"
                "5️⃣ Donne un nom (ex: CryptoCoach)\n"
                "6️⃣ Coche UNIQUEMENT ✅ *Accès aux données du compte*\n"
                "❌ Ne coche JAMAIS Trading ou Transfert\n\n"
                "🔗 Lien direct : kraken.com/u/security/api"
            ),
            "en": (
                "📖 *How to create your Kraken API keys:*\n\n"
                "1️⃣ Go to kraken.com → log in\n"
                "2️⃣ Click your name → *Security*\n"
                "3️⃣ Select *API*\n"
                "4️⃣ Click *Add key*\n"
                "5️⃣ Give it a name (e.g. CryptoCoach)\n"
                "6️⃣ Check ONLY ✅ *Query account data*\n"
                "❌ NEVER enable Trading or Transfer\n\n"
                "🔗 Direct link: kraken.com/u/security/api"
            ),
            "es": (
                "📖 *Cómo crear tus claves API de Kraken:*\n\n"
                "1️⃣ Ve a kraken.com → inicia sesión\n"
                "2️⃣ Haz clic en tu nombre → *Seguridad*\n"
                "3️⃣ Selecciona *API*\n"
                "4️⃣ Haz clic en *Agregar clave*\n"
                "5️⃣ Dale un nombre (ej: CryptoCoach)\n"
                "6️⃣ Marca SOLO ✅ *Consultar datos de cuenta*\n"
                "❌ NUNCA actives Trading o Transferencia\n\n"
                "🔗 Enlace directo: kraken.com/u/security/api"
            ),
            "pt": (
                "📖 *Como criar suas chaves API da Kraken:*\n\n"
                "1️⃣ Vá para kraken.com → faça login\n"
                "2️⃣ Clique no seu nome → *Segurança*\n"
                "3️⃣ Selecione *API*\n"
                "4️⃣ Clique em *Adicionar chave*\n"
                "5️⃣ Dê um nome (ex: CryptoCoach)\n"
                "6️⃣ Marque APENAS ✅ *Consultar dados da conta*\n"
                "❌ NUNCA ative Trading ou Transferência\n\n"
                "🔗 Link direto: kraken.com/u/security/api"
            ),
        },
    }

# ─── /exchange ───────────────────────────────────────────────────

@router.message(Command("exchange"))
async def cmd_exchange(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "en"

    connected = await get_user_exchanges(user_id)

    builder = InlineKeyboardBuilder()
    for ex_id, ex_name in SUPPORTED_EXCHANGES.items():
        status = "✅" if ex_id in connected else "➕"
        builder.button(
            text=f"{status} {ex_name}",
            callback_data=f"exchange_select:{ex_id}"
        )
    builder.adjust(1)

    titles = {
        "fr": "🔗 *Connexion Exchange*\n\nChoisis un exchange à connecter :",
        "en": "🔗 *Exchange Connection*\n\nChoose an exchange to connect:",
        "es": "🔗 *Conexión Exchange*\n\nElige un exchange para conectar:",
        "pt": "🔗 *Conexão Exchange*\n\nEscolha uma exchange para conectar:",
    }

    await message.answer(
        titles.get(lang, titles["en"]),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("exchange_select:"))
async def process_exchange_select(callback: CallbackQuery, state: FSMContext):
    exchange_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "en"

    await state.update_data(language=lang, exchange_id=exchange_id)
    existing = await get_exchange_connection(user_id, exchange_id)

    if existing:
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Reconnecter", callback_data=f"exchange_reconnect:{exchange_id}")
        builder.button(text="🗑️ Déconnecter", callback_data=f"exchange_disconnect:{exchange_id}")
        builder.button(text="📊 Voir mes trades", callback_data=f"exchange_trades:{exchange_id}")
        builder.adjust(1)

        already_texts = {
            "fr": f"✅ *{SUPPORTED_EXCHANGES[exchange_id]}* est déjà connecté.\nQue veux-tu faire ?",
            "en": f"✅ *{SUPPORTED_EXCHANGES[exchange_id]}* is already connected.\nWhat do you want to do?",
            "es": f"✅ *{SUPPORTED_EXCHANGES[exchange_id]}* ya está conectado.\n¿Qué quieres hacer?",
            "pt": f"✅ *{SUPPORTED_EXCHANGES[exchange_id]}* já está conectado.\nO que você quer fazer?",
        }
        await callback.message.edit_text(
            already_texts.get(lang, already_texts["en"]),
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    await start_api_key_flow(callback.message, state, exchange_id, lang)
    await callback.answer()

# ─── Flux de connexion ───────────────────────────────────────────

async def start_api_key_flow(message, state, exchange_id, lang):
    """Lance le flux avec instructions puis demande la clé API."""

    # Instructions spécifiques à l'exchange
    instructions = EXCHANGE_API_INSTRUCTIONS.get(exchange_id, {})
    instruction_text = instructions.get(lang, instructions.get("en", ""))

    if instruction_text:
        await message.answer(instruction_text, parse_mode="Markdown")

    # Demande de clé
    security_texts = {
        "fr": "✅ *Clés prêtes ?*\n\nEnvoie maintenant ta *clé API* :",
        "en": "✅ *Keys ready?*\n\nNow send your *API Key* :",
        "es": "✅ *¿Claves listas?*\n\nEnvía ahora tu *clave API* :",
        "pt": "✅ *Chaves prontas?*\n\nEnvie agora sua *chave API* :",
    }

    await message.answer(
        security_texts.get(lang, security_texts["en"]),
        parse_mode="Markdown"
    )
    await state.set_state(ExchangeSetup.waiting_api_key)

@router.message(ExchangeSetup.waiting_api_key)
async def process_api_key(message: Message, state: FSMContext):
    api_key = message.text.strip()
    await state.update_data(api_key=api_key)
    await message.delete()

    data = await state.get_data()
    lang = data.get("language", "en")

    secret_texts = {
        "fr": "✅ Clé API reçue (message supprimé pour sécurité).\n\nEnvoie maintenant ton *Secret API* :",
        "en": "✅ API Key received (message deleted for security).\n\nNow send your *API Secret* :",
        "es": "✅ Clave API recibida (mensaje eliminado).\n\nEnvía ahora tu *Secret API* :",
        "pt": "✅ Chave API recebida (mensagem apagada).\n\nEnvie agora seu *Secret API* :",
    }

    await message.answer(
        secret_texts.get(lang, secret_texts["en"]),
        parse_mode="Markdown"
    )
    await state.set_state(ExchangeSetup.waiting_api_secret)

@router.message(ExchangeSetup.waiting_api_secret)
async def process_api_secret(message: Message, state: FSMContext):
    api_secret = message.text.strip()
    await message.delete()

    data = await state.get_data()
    lang = data.get("language", "en")
    exchange_id = data.get("exchange_id")
    api_key = data.get("api_key")
    user_id = message.from_user.id

    testing_texts = {
        "fr": "🔄 Test de connexion en cours...",
        "en": "🔄 Testing connection...",
        "es": "🔄 Probando conexión...",
        "pt": "🔄 Testando conexão...",
    }
    status_msg = await message.answer(testing_texts.get(lang, testing_texts["en"]))
    result = await test_connection(exchange_id, api_key, api_secret)

    if result["success"]:
        await save_exchange_connection(user_id, exchange_id, api_key, api_secret)
        await state.clear()

        success_texts = {
            "fr": (
                f"✅ *{SUPPORTED_EXCHANGES[exchange_id]} connecté !*\n\n"
                f"J'ai détecté {result['assets_count']} actif(s).\n\n"
                "Utilise /trades pour analyser tes transactions."
            ),
            "en": (
                f"✅ *{SUPPORTED_EXCHANGES[exchange_id]} connected!*\n\n"
                f"I detected {result['assets_count']} asset(s).\n\n"
                "Use /trades to analyze your transactions."
            ),
            "es": (
                f"✅ *¡{SUPPORTED_EXCHANGES[exchange_id]} conectado!*\n\n"
                f"Detecté {result['assets_count']} activo(s).\n\n"
                "Usa /trades para analizar tus transacciones."
            ),
            "pt": (
                f"✅ *{SUPPORTED_EXCHANGES[exchange_id]} conectado!*\n\n"
                f"Detectei {result['assets_count']} ativo(s).\n\n"
                "Use /trades para analisar suas transações."
            ),
        }
        await status_msg.edit_text(
            success_texts.get(lang, success_texts["en"]),
            parse_mode="Markdown"
        )
    else:
        error_texts = {
            "fr": f"❌ Connexion échouée : {result['message']}\n\nVérifie tes clés et réessaie avec /exchange",
            "en": f"❌ Connection failed: {result['message']}\n\nCheck your keys and retry with /exchange",
            "es": f"❌ Conexión fallida: {result['message']}\n\nVerifica tus claves y reintenta con /exchange",
            "pt": f"❌ Conexão falhou: {result['message']}\n\nVerifique suas chaves e tente com /exchange",
        }
        await status_msg.edit_text(error_texts.get(lang, error_texts["en"]))
        await state.clear()

# ─── /trades ─────────────────────────────────────────────────────

@router.message(Command("trades"))
async def cmd_trades(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "en"

    exchanges = await get_user_exchanges(user_id)

    if not exchanges:
        no_exchange_texts = {
            "fr": "❌ Aucun exchange connecté. Utilise /exchange pour connecter un exchange.",
            "en": "❌ No exchange connected. Use /exchange to connect one.",
            "es": "❌ Ningún exchange conectado. Usa /exchange para conectar.",
            "pt": "❌ Nenhuma exchange conectada. Use /exchange para conectar.",
        }
        await message.answer(no_exchange_texts.get(lang, no_exchange_texts["en"]))
        return

    loading_texts = {
        "fr": "📊 Récupération de tes trades...",
        "en": "📊 Fetching your trades...",
        "es": "📊 Obteniendo tus trades...",
        "pt": "📊 Buscando seus trades...",
    }
    status_msg = await message.answer(loading_texts.get(lang, loading_texts["en"]))

    exchange_id = exchanges[0]
    conn = await get_exchange_connection(user_id, exchange_id)
    trades = await fetch_recent_trades(exchange_id, conn["api_key"], conn["api_secret"])

    if not trades:
        no_trades_texts = {
            "fr": "📭 Aucun trade récent trouvé.",
            "en": "📭 No recent trades found.",
            "es": "📭 No se encontraron trades recientes.",
            "pt": "📭 Nenhum trade recente encontrado.",
        }
        await status_msg.edit_text(no_trades_texts.get(lang, no_trades_texts["en"]))
        return

    trades_text = format_trades_for_analysis(trades)

    analysis_prompts = {
        "fr": f"Voici mes trades récents:\n\n{trades_text}\n\nAnalyse et donne-moi un feedback personnalisé.",
        "en": f"Here are my recent trades:\n\n{trades_text}\n\nAnalyze and give me personalized feedback.",
        "es": f"Aquí están mis trades recientes:\n\n{trades_text}\n\nAnaliza y dame feedback personalizado.",
        "pt": f"Aqui estão meus trades recentes:\n\n{trades_text}\n\nAnalise e me dê feedback personalizado.",
    }

    analysis = await get_coaching_response(
        analysis_prompts.get(lang, analysis_prompts["en"]),
        lang, user, []
    )

    await status_msg.edit_text(
        f"📊 *{len(trades)} derniers trades — {SUPPORTED_EXCHANGES[exchange_id]}*\n\n`{trades_text}`",
        parse_mode="Markdown"
    )
    await message.answer(f"🧠 *Analyse :*\n\n{analysis}", parse_mode="Markdown")

# ─── Déconnexion / Reconnexion ───────────────────────────────────

@router.callback_query(F.data.startswith("exchange_disconnect:"))
async def process_disconnect(callback: CallbackQuery):
    exchange_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "en"

    await delete_exchange_connection(user_id, exchange_id)

    disconnected_texts = {
        "fr": f"✅ {SUPPORTED_EXCHANGES[exchange_id]} déconnecté.",
        "en": f"✅ {SUPPORTED_EXCHANGES[exchange_id]} disconnected.",
        "es": f"✅ {SUPPORTED_EXCHANGES[exchange_id]} desconectado.",
        "pt": f"✅ {SUPPORTED_EXCHANGES[exchange_id]} desconectado.",
    }
    await callback.message.edit_text(disconnected_texts.get(lang, disconnected_texts["en"]))
    await callback.answer()

@router.callback_query(F.data.startswith("exchange_reconnect:"))
async def process_reconnect(callback: CallbackQuery, state: FSMContext):
    exchange_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "en"

    await state.update_data(language=lang, exchange_id=exchange_id)
    await start_api_key_flow(callback.message, state, exchange_id, lang)
    await callback.answer()

@router.callback_query(F.data.startswith("exchange_trades:"))
async def process_view_trades(callback: CallbackQuery):
    await callback.message.answer("/trades")
    await callback.answer()
    # ─── Fallback — messages sans état défini ───────────────────────

    @router.message()
    async def fallback_message(message: Message, state: FSMContext):
        """Attrape tous les messages non gérés par les autres handlers."""
        user_id = message.from_user.id
        user = await get_user(user_id)

        if not user or not user.get("level"):
            await message.answer("Envoie /start pour commencer.")
            return

        lang = user["language"]
        # Vérifier la limite freemium
        if not await check_free_limit(message, lang):
            return

        # Remettre l'état coaching et traiter le message
        await state.update_data(language=lang)
        await state.set_state(ProfileSetup.coaching)

        thinking_msg = await message.answer(TEXTS["thinking"][lang])
        history = await get_conversation_history(user_id)

        response = await get_coaching_response(
            message.text, lang, user, history
        )

        await save_message(user_id, "user", message.text)
        await save_message(user_id, "assistant", response)
        await update_xp(user_id, 5)

        streak, streak_badge = await update_streak(user_id, lang)
        first_msg_badge = await check_and_award_badge(user_id, "first_message", lang)

        await thinking_msg.delete()
        await message.answer(response)

        if first_msg_badge:
            await message.answer(first_msg_badge, parse_mode="Markdown")
        if streak_badge:
            await message.answer(streak_badge, parse_mode="Markdown")