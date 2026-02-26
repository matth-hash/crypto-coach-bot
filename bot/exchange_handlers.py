from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import (
    get_user, save_exchange_connection, get_exchange_connection,
    get_user_exchanges, delete_exchange_connection
)
from exchange_manager import (
    test_connection, fetch_recent_trades,
    format_trades_for_analysis, SUPPORTED_EXCHANGES
)
from ai_coach import get_coaching_response

router = Router()

class ExchangeSetup(StatesGroup):
    choosing_exchange = State()
    waiting_api_key = State()
    waiting_api_secret = State()

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

async def start_api_key_flow(message, state, exchange_id, lang):
    security_texts = {
        "fr": (
            f"🔐 *Connexion {SUPPORTED_EXCHANGES[exchange_id]}*\n\n"
            "⚠️ *Sécurité importante :*\n"
            "• Crée des clés API en *lecture seule* uniquement\n"
            "• N'active jamais la permission de retrait\n"
            "• Tes clés sont chiffrées dans notre base\n\n"
            "Envoie maintenant ta *clé API* :"
        ),
        "en": (
            f"🔐 *{SUPPORTED_EXCHANGES[exchange_id]} Connection*\n\n"
            "⚠️ *Important security:*\n"
            "• Create API keys with *read only* permissions\n"
            "• Never enable withdrawal permission\n"
            "• Your keys are encrypted in our database\n\n"
            "Now send your *API Key* :"
        ),
        "es": (
            f"🔐 *Conexión {SUPPORTED_EXCHANGES[exchange_id]}*\n\n"
            "⚠️ *Seguridad importante:*\n"
            "• Crea claves API de *solo lectura*\n"
            "• Nunca actives el permiso de retiro\n"
            "• Tus claves están cifradas\n\n"
            "Envía ahora tu *clave API* :"
        ),
        "pt": (
            f"🔐 *Conexão {SUPPORTED_EXCHANGES[exchange_id]}*\n\n"
            "⚠️ *Segurança importante:*\n"
            "• Crie chaves API de *somente leitura*\n"
            "• Nunca ative a permissão de saque\n"
            "• Suas chaves são criptografadas\n\n"
            "Envie agora sua *chave API* :"
        ),
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

@router.message(Command("trades"))
async def cmd_trades(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "en"

    exchanges = await get_user_exchanges(user_id)

    if not exchanges:
        no_exchange_texts = {
            "fr": "❌ Aucun exchange connecté. Utilise /exchange pour connecter Binance ou Bybit.",
            "en": "❌ No exchange connected. Use /exchange to connect Binance or Bybit.",
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