from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import (
    get_user, save_journal_trade, get_journal_trades,
    save_postmortem, delete_journal_trade, update_xp,
    get_user_exchanges, get_exchange_connection
)
from ai_coach import get_coaching_response
from market_data import TOP_50_CRYPTOS, STOCKS, INDICES

router = Router()

# Symboles rapides pour le journal
QUICK_SYMBOLS = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "DOT", "LINK"]

EMOTIONS = {
    "fr": [("😰 FOMO", "fomo"), ("😎 Confiant", "confident"), ("😰 Stressé", "stressed"), ("😐 Neutre", "neutral"), ("🤑 Avidité", "greed")],
    "en": [("😰 FOMO", "fomo"), ("😎 Confident", "confident"), ("😰 Stressed", "stressed"), ("😐 Neutral", "neutral"), ("🤑 Greed", "greed")],
    "es": [("😰 FOMO", "fomo"), ("😎 Confiado", "confident"), ("😰 Estresado", "stressed"), ("😐 Neutral", "neutral"), ("🤑 Avaricia", "greed")],
    "pt": [("😰 FOMO", "fomo"), ("😎 Confiante", "confident"), ("😰 Estressado", "stressed"), ("😐 Neutro", "neutral"), ("🤑 Ganância", "greed")],
}

class JournalSetup(StatesGroup):
    waiting_symbol = State()
    waiting_custom_symbol = State()
    waiting_side = State()
    waiting_entry_price = State()
    waiting_exit_price = State()
    waiting_amount = State()
    waiting_emotion = State()
    waiting_reason = State()

# ─── /journal ─────────────────────────────────────────────────────

@router.message(Command("journal"))
async def cmd_journal(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "fr"
    await state.update_data(language=lang)

    builder = InlineKeyboardBuilder()
    labels = {
        "fr": [("➕ Ajouter un trade", "journal_add"), ("📥 Importer depuis exchange", "journal_import"), ("📋 Mes trades", "journal_list"), ("🧠 Post-mortem IA", "journal_postmortem")],
        "en": [("➕ Add a trade", "journal_add"), ("📥 Import from exchange", "journal_import"), ("📋 My trades", "journal_list"), ("🧠 AI Post-mortem", "journal_postmortem")],
        "es": [("➕ Agregar un trade", "journal_add"), ("📥 Importar desde exchange", "journal_import"), ("📋 Mis trades", "journal_list"), ("🧠 Post-mortem IA", "journal_postmortem")],
        "pt": [("➕ Adicionar um trade", "journal_add"), ("📥 Importar do exchange", "journal_import"), ("📋 Meus trades", "journal_list"), ("🧠 Post-mortem IA", "journal_postmortem")],
    }
    for text, cb in labels.get(lang, labels["fr"]):
        builder.button(text=text, callback_data=cb)
    builder.adjust(1)

    titles = {
        "fr": "📓 *Journal de Trading*\n\nEnregistre tes trades avec contexte émotionnel et obtiens une analyse IA personnalisée.",
        "en": "📓 *Trading Journal*\n\nRecord your trades with emotional context and get personalized AI analysis.",
        "es": "📓 *Diario de Trading*\n\nRegistra tus trades con contexto emocional y obtén análisis IA personalizado.",
        "pt": "📓 *Diário de Trading*\n\nRegistre seus trades com contexto emocional e obtenha análise IA personalizada.",
    }
    await message.answer(titles.get(lang, titles["fr"]), reply_markup=builder.as_markup(), parse_mode="Markdown")

# ─── /score ───────────────────────────────────────────────────────

@router.message(Command("score"))
async def cmd_score(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "fr"

    loading = {"fr": "📊 Calcul du score en cours...", "en": "📊 Calculating score...", "es": "📊 Calculando score...", "pt": "📊 Calculando score..."}
    msg = await message.answer(loading.get(lang, loading["fr"]))

    from market_data import get_market_score, get_fear_greed_index, get_crypto_prices
    score_data, fg, prices = await __import__("asyncio").gather(
        get_market_score(), get_fear_greed_index(), get_crypto_prices()
    )

    score = score_data.get("score", 50)
    label = score_data.get("label", {}).get(lang, "🟡 Neutre")
    btc_change = prices.get("BTC", {}).get("change_24h", 0)
    eth_change = prices.get("ETH", {}).get("change_24h", 0)

    texts = {
        "fr": (
            f"📊 *Score de Marché*\n\n"
            f"**{score}/100** — {label}\n\n"
            f"📈 Composantes :\n"
            f"• Fear & Greed : {score_data.get('fg', 50)}/100\n"
            f"• BTC 24h : {btc_change:+.1f}%\n"
            f"• ETH 24h : {eth_change:+.1f}%\n"
            f"• Dominance BTC : {score_data.get('dominance', 50):.1f}%\n\n"
            f"_Score mis à jour toutes les 5 min_"
        ),
        "en": (
            f"📊 *Market Score*\n\n"
            f"**{score}/100** — {label}\n\n"
            f"📈 Components:\n"
            f"• Fear & Greed: {score_data.get('fg', 50)}/100\n"
            f"• BTC 24h: {btc_change:+.1f}%\n"
            f"• ETH 24h: {eth_change:+.1f}%\n"
            f"• BTC Dominance: {score_data.get('dominance', 50):.1f}%\n\n"
            f"_Score updated every 5 min_"
        ),
        "es": (
            f"📊 *Score de Mercado*\n\n"
            f"**{score}/100** — {label}\n\n"
            f"📈 Componentes:\n"
            f"• Fear & Greed: {score_data.get('fg', 50)}/100\n"
            f"• BTC 24h: {btc_change:+.1f}%\n"
            f"• ETH 24h: {eth_change:+.1f}%\n"
            f"• Dominancia BTC: {score_data.get('dominance', 50):.1f}%\n\n"
            f"_Score actualizado cada 5 min_"
        ),
        "pt": (
            f"📊 *Score de Mercado*\n\n"
            f"**{score}/100** — {label}\n\n"
            f"📈 Componentes:\n"
            f"• Fear & Greed: {score_data.get('fg', 50)}/100\n"
            f"• BTC 24h: {btc_change:+.1f}%\n"
            f"• ETH 24h: {eth_change:+.1f}%\n"
            f"• Dominância BTC: {score_data.get('dominance', 50):.1f}%\n\n"
            f"_Score atualizado a cada 5 min_"
        ),
    }
    await msg.edit_text(texts.get(lang, texts["fr"]), parse_mode="Markdown")

# ─── Import depuis exchange ───────────────────────────────────────

@router.callback_query(F.data == "journal_import")
async def cb_journal_import(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "fr"

    exchanges = await get_user_exchanges(user_id)
    if not exchanges:
        no_ex = {
            "fr": "❌ Aucun exchange connecté.\n\nUtilise /exchange pour connecter Binance, Bybit...",
            "en": "❌ No exchange connected.\n\nUse /exchange to connect Binance, Bybit...",
            "es": "❌ Ningún exchange conectado.\n\nUsa /exchange para conectar Binance, Bybit...",
            "pt": "❌ Nenhuma exchange conectada.\n\nUse /exchange para conectar Binance, Bybit...",
        }
        await callback.message.edit_text(no_ex.get(lang, no_ex["fr"]))
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    for ex in exchanges:
        builder.button(text=f"🔗 {ex.capitalize()}", callback_data=f"journal_import_ex:{ex}")
    builder.adjust(1)

    titles = {
        "fr": "📥 *Importer des trades*\n\nChoisis l'exchange à importer :",
        "en": "📥 *Import trades*\n\nChoose the exchange to import from:",
        "es": "📥 *Importar trades*\n\nElige el exchange a importar:",
        "pt": "📥 *Importar trades*\n\nEscolha a exchange para importar:",
    }
    await callback.message.edit_text(titles.get(lang, titles["fr"]), reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("journal_import_ex:"))
async def cb_journal_import_exchange(callback: CallbackQuery, state: FSMContext):
    exchange_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "fr"

    loading = {
        "fr": f"🔄 Import depuis {exchange_id.capitalize()} en cours...",
        "en": f"🔄 Importing from {exchange_id.capitalize()}...",
        "es": f"🔄 Importando desde {exchange_id.capitalize()}...",
        "pt": f"🔄 Importando de {exchange_id.capitalize()}...",
    }
    await callback.message.edit_text(loading.get(lang, loading["fr"]))

    conn = await get_exchange_connection(user_id, exchange_id)
    if not conn:
        await callback.message.edit_text("❌ Exchange non trouvé.")
        await callback.answer()
        return

    from exchange_manager import fetch_recent_trades
    trades = await fetch_recent_trades(exchange_id, conn["api_key"], conn["api_secret"], limit=20)

    if not trades:
        empty = {
            "fr": "📭 Aucun trade récent trouvé sur cet exchange.",
            "en": "📭 No recent trades found on this exchange.",
            "es": "📭 No se encontraron trades recientes en este exchange.",
            "pt": "📭 Nenhum trade recente encontrado nesta exchange.",
        }
        await callback.message.edit_text(empty.get(lang, empty["fr"]))
        await callback.answer()
        return

    # Import dans le journal
    imported = 0
    for t in trades:
        try:
            symbol = t["symbol"].replace("/USDT", "").replace("/USD", "").replace("/USDC", "")
            await save_journal_trade(
                user_id=user_id,
                symbol=symbol,
                side=t["side"],
                entry_price=float(t["price"]),
                exit_price=None,
                amount=float(t["cost"]) if t.get("cost") else float(t["amount"]) * float(t["price"]),
                emotion="neutral",
                reason=f"Import {exchange_id}",
            )
            imported += 1
        except Exception:
            continue

    await update_xp(user_id, imported * 2)

    success = {
        "fr": f"✅ *{imported} trade(s) importés* depuis {exchange_id.capitalize()} !\n\nUtilise /journal → Post-mortem IA pour les analyser.",
        "en": f"✅ *{imported} trade(s) imported* from {exchange_id.capitalize()}!\n\nUse /journal → AI Post-mortem to analyze them.",
        "es": f"✅ *{imported} trade(s) importados* desde {exchange_id.capitalize()}!\n\nUsa /journal → Post-mortem IA para analizarlos.",
        "pt": f"✅ *{imported} trade(s) importados* de {exchange_id.capitalize()}!\n\nUse /journal → Post-mortem IA para analisá-los.",
    }
    await callback.message.edit_text(success.get(lang, success["fr"]), parse_mode="Markdown")
    await callback.answer()

# ─── Ajouter un trade manuel ─────────────────────────────────────

@router.callback_query(F.data == "journal_add")
async def cb_journal_add(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "fr")

    builder = InlineKeyboardBuilder()
    # Top 10 rapides
    for symbol in QUICK_SYMBOLS:
        builder.button(text=f"🪙 {symbol}", callback_data=f"journal_symbol:{symbol}")
    # Catégories étendues
    cat_labels = {"fr": "📈 Actions US", "en": "📈 US Stocks", "es": "📈 Acciones US", "pt": "📈 Ações US"}
    builder.button(text=cat_labels.get(lang, cat_labels["fr"]), callback_data="journal_cat:stocks")
    builder.button(text="📊 Indices & Matières", callback_data="journal_cat:indices")
    other_labels = {"fr": "⌨️ Autre symbole", "en": "⌨️ Other symbol", "es": "⌨️ Otro símbolo", "pt": "⌨️ Outro símbolo"}
    builder.button(text=other_labels.get(lang, other_labels["fr"]), callback_data="journal_symbol:AUTRE")
    builder.adjust(4)

    texts = {
        "fr": "🪙 *Nouveau trade*\n\nSur quel actif ?",
        "en": "🪙 *New trade*\n\nWhich asset?",
        "es": "🪙 *Nuevo trade*\n\n¿En qué activo?",
        "pt": "🪙 *Novo trade*\n\nEm qual ativo?",
    }
    await callback.message.edit_text(texts.get(lang, texts["fr"]), reply_markup=builder.as_markup(), parse_mode="Markdown")
    await state.set_state(JournalSetup.waiting_symbol)
    await callback.answer()

@router.callback_query(JournalSetup.waiting_symbol, F.data.startswith("journal_cat:"))
async def cb_journal_category(callback: CallbackQuery, state: FSMContext):
    cat = callback.data.split(":")[1]
    data = await state.get_data()
    lang = data.get("language", "fr")

    builder = InlineKeyboardBuilder()
    if cat == "stocks":
        for symbol, name in STOCKS.items():
            builder.button(text=f"📈 {symbol}", callback_data=f"journal_symbol:{symbol}")
        builder.adjust(3)
    elif cat == "indices":
        labels = {"^GSPC": "SP500", "^IXIC": "NASDAQ", "^FCHI": "CAC40", "^GDAXI": "DAX", "GC=F": "🥇 Gold", "SI=F": "🥈 Silver", "CL=F": "🛢 Oil"}
        for ticker, name in labels.items():
            builder.button(text=name, callback_data=f"journal_symbol:{name}")
        builder.adjust(3)

    back_labels = {"fr": "◀️ Retour", "en": "◀️ Back", "es": "◀️ Volver", "pt": "◀️ Voltar"}
    builder.button(text=back_labels.get(lang, back_labels["fr"]), callback_data="journal_add")
    await callback.message.edit_text("Choisis un actif :", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(JournalSetup.waiting_symbol, F.data.startswith("journal_symbol:"))
async def cb_journal_symbol(callback: CallbackQuery, state: FSMContext):
    symbol = callback.data.split(":")[1]
    data = await state.get_data()
    lang = data.get("language", "fr")

    if symbol == "AUTRE":
        texts = {
            "fr": "⌨️ Saisis le symbole _(ex: MATIC, LINK, AAPL)_ :",
            "en": "⌨️ Type the symbol _(e.g. MATIC, LINK, AAPL)_ :",
            "es": "⌨️ Escribe el símbolo _(ej: MATIC, LINK, AAPL)_ :",
            "pt": "⌨️ Digite o símbolo _(ex: MATIC, LINK, AAPL)_ :",
        }
        await callback.message.edit_text(texts.get(lang, texts["fr"]), parse_mode="Markdown")
        await state.set_state(JournalSetup.waiting_custom_symbol)
        await callback.answer()
        return

    await state.update_data(symbol=symbol)
    await _ask_side(callback.message, lang, state, edit=True)
    await callback.answer()

@router.message(JournalSetup.waiting_custom_symbol)
async def process_custom_symbol(message: Message, state: FSMContext):
    symbol = message.text.strip().upper()[:10]
    await state.update_data(symbol=symbol)
    data = await state.get_data()
    lang = data.get("language", "fr")
    await _ask_side(message, lang, state, edit=False)

async def _ask_side(msg, lang, state, edit=False):
    builder = InlineKeyboardBuilder()
    labels = {
        "fr": [("🟢 ACHAT", "buy"), ("🔴 VENTE", "sell")],
        "en": [("🟢 BUY", "buy"), ("🔴 SELL", "sell")],
        "es": [("🟢 COMPRA", "buy"), ("🔴 VENTA", "sell")],
        "pt": [("🟢 COMPRA", "buy"), ("🔴 VENDA", "sell")],
    }
    for text, val in labels.get(lang, labels["fr"]):
        builder.button(text=text, callback_data=f"journal_side:{val}")
    builder.adjust(2)
    texts = {"fr": "📊 Direction du trade :", "en": "📊 Trade direction:", "es": "📊 Dirección del trade:", "pt": "📊 Direção do trade:"}
    if edit:
        await msg.edit_text(texts.get(lang, texts["fr"]), reply_markup=builder.as_markup())
    else:
        await msg.answer(texts.get(lang, texts["fr"]), reply_markup=builder.as_markup())
    await state.set_state(JournalSetup.waiting_side)

@router.callback_query(JournalSetup.waiting_side, F.data.startswith("journal_side:"))
async def cb_journal_side(callback: CallbackQuery, state: FSMContext):
    side = callback.data.split(":")[1]
    data = await state.get_data()
    lang = data.get("language", "fr")
    await state.update_data(side=side)
    texts = {"fr": "💰 *Prix d'entrée* en $ _(ex: 65000)_ :", "en": "💰 *Entry price* in $ _(e.g. 65000)_ :", "es": "💰 *Precio de entrada* en $ _(ej: 65000)_ :", "pt": "💰 *Preço de entrada* em $ _(ex: 65000)_ :"}
    await callback.message.edit_text(texts.get(lang, texts["fr"]), parse_mode="Markdown")
    await state.set_state(JournalSetup.waiting_entry_price)
    await callback.answer()

@router.message(JournalSetup.waiting_entry_price)
async def process_entry_price(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "fr")
    try:
        price = float(message.text.strip().replace(",", ".").replace(" ", ""))
        if price <= 0: raise ValueError
    except ValueError:
        await message.answer({"fr": "❌ Prix invalide. Ex: *65000*", "en": "❌ Invalid price. E.g.: *65000*", "es": "❌ Precio inválido. Ej: *65000*", "pt": "❌ Preço inválido. Ex: *65000*"}.get(lang, "❌ Invalid"), parse_mode="Markdown")
        return

    await state.update_data(entry_price=price)

    builder = InlineKeyboardBuilder()
    skip_labels = {"fr": "⏭ Position encore ouverte", "en": "⏭ Position still open", "es": "⏭ Posición aún abierta", "pt": "⏭ Posição ainda aberta"}
    builder.button(text=skip_labels.get(lang, skip_labels["fr"]), callback_data="journal_exit_skip")
    texts = {"fr": "💰 *Prix de sortie* en $ _(ou ignore si ouverte)_ :", "en": "💰 *Exit price* in $ _(or skip if still open)_ :", "es": "💰 *Precio de salida* en $ _(o ignora si abierta)_ :", "pt": "💰 *Preço de saída* em $ _(ou ignore se aberta)_ :"}
    await message.answer(texts.get(lang, texts["fr"]), reply_markup=builder.as_markup(), parse_mode="Markdown")
    await state.set_state(JournalSetup.waiting_exit_price)

@router.callback_query(JournalSetup.waiting_exit_price, F.data == "journal_exit_skip")
async def cb_exit_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(exit_price=None)
    data = await state.get_data()
    lang = data.get("language", "fr")
    await callback.message.edit_reply_markup()
    await _ask_amount(callback.message, lang, state, edit=False)
    await callback.answer()

@router.message(JournalSetup.waiting_exit_price)
async def process_exit_price(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "fr")
    try:
        price = float(message.text.strip().replace(",", ".").replace(" ", ""))
        if price <= 0: raise ValueError
    except ValueError:
        await message.answer({"fr": "❌ Prix invalide.", "en": "❌ Invalid price.", "es": "❌ Precio inválido.", "pt": "❌ Preço inválido."}.get(lang, "❌"), parse_mode="Markdown")
        return
    await state.update_data(exit_price=price)
    await _ask_amount(message, lang, state, edit=False)

async def _ask_amount(msg, lang, state, edit=False):
    texts = {"fr": "📦 *Montant investi* en $ _(ex: 500)_ :", "en": "📦 *Amount invested* in $ _(e.g. 500)_ :", "es": "📦 *Monto invertido* en $ _(ej: 500)_ :", "pt": "📦 *Valor investido* em $ _(ex: 500)_ :"}
    if edit:
        await msg.edit_text(texts.get(lang, texts["fr"]), parse_mode="Markdown")
    else:
        await msg.answer(texts.get(lang, texts["fr"]), parse_mode="Markdown")
    await state.set_state(JournalSetup.waiting_amount)

@router.message(JournalSetup.waiting_amount)
async def process_amount(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "fr")
    try:
        amount = float(message.text.strip().replace(",", ".").replace(" ", ""))
        if amount <= 0: raise ValueError
    except ValueError:
        await message.answer({"fr": "❌ Montant invalide. Ex: *500*", "en": "❌ Invalid amount. E.g.: *500*", "es": "❌ Monto inválido. Ej: *500*", "pt": "❌ Valor inválido. Ex: *500*"}.get(lang, "❌"), parse_mode="Markdown")
        return
    await state.update_data(amount=amount)

    builder = InlineKeyboardBuilder()
    for label, val in EMOTIONS.get(lang, EMOTIONS["fr"]):
        builder.button(text=label, callback_data=f"journal_emotion:{val}")
    builder.adjust(2)
    texts = {"fr": "🧠 *État émotionnel* au moment du trade :", "en": "🧠 *Emotional state* at trade time:", "es": "🧠 *Estado emocional* en el momento del trade:", "pt": "🧠 *Estado emocional* no momento do trade:"}
    await message.answer(texts.get(lang, texts["fr"]), reply_markup=builder.as_markup(), parse_mode="Markdown")
    await state.set_state(JournalSetup.waiting_emotion)

@router.callback_query(JournalSetup.waiting_emotion, F.data.startswith("journal_emotion:"))
async def cb_journal_emotion(callback: CallbackQuery, state: FSMContext):
    emotion = callback.data.split(":")[1]
    data = await state.get_data()
    lang = data.get("language", "fr")
    await state.update_data(emotion=emotion)
    await callback.message.edit_reply_markup()
    texts = {"fr": "✍️ *Raison du trade* — pourquoi cette position ? _(1-2 phrases)_", "en": "✍️ *Trade reason* — why this position? _(1-2 sentences)_", "es": "✍️ *Razón del trade* — ¿por qué esta posición? _(1-2 frases)_", "pt": "✍️ *Motivo do trade* — por que essa posição? _(1-2 frases)_"}
    await callback.message.answer(texts.get(lang, texts["fr"]), parse_mode="Markdown")
    await state.set_state(JournalSetup.waiting_reason)
    await callback.answer()

@router.message(JournalSetup.waiting_reason)
async def process_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "fr")
    reason = message.text.strip()[:500]
    user_id = message.from_user.id

    await save_journal_trade(
        user_id=user_id, symbol=data["symbol"], side=data["side"],
        entry_price=data["entry_price"], exit_price=data.get("exit_price"),
        amount=data["amount"], emotion=data["emotion"], reason=reason,
    )
    await update_xp(user_id, 10)
    await state.clear()

    exit_price = data.get("exit_price")
    side_emoji = "🟢" if data["side"] == "buy" else "🔴"

    side_labels = {
        "buy":  {"fr": "ACHAT", "en": "BUY", "es": "COMPRA", "pt": "COMPRA"},
        "sell": {"fr": "VENTE", "en": "SELL", "es": "VENTA", "pt": "VENDA"},
    }
    side_label = side_labels[data["side"]].get(lang, data["side"].upper())

    pnl_line = ""
    if exit_price:
        if data["side"] == "buy":
            pnl = (exit_price - data["entry_price"]) * data["amount"] / data["entry_price"]
            pnl_pct = ((exit_price - data["entry_price"]) / data["entry_price"]) * 100
        else:
            pnl = (data["entry_price"] - exit_price) * data["amount"] / data["entry_price"]
            pnl_pct = ((data["entry_price"] - exit_price) / data["entry_price"]) * 100
        pnl_emoji = "🟢" if pnl >= 0 else "🔴"
        pnl_line = f"\n💰 P&L : {pnl_emoji} ${pnl:+.2f} ({pnl_pct:+.1f}%)"

    exit_str = {
        "fr": f"📤 Sortie : ${exit_price:,.2f}" if exit_price else "📤 Position : encore ouverte",
        "en": f"📤 Exit: ${exit_price:,.2f}" if exit_price else "📤 Position: still open",
        "es": f"📤 Salida: ${exit_price:,.2f}" if exit_price else "📤 Posición: aún abierta",
        "pt": f"📤 Saída: ${exit_price:,.2f}" if exit_price else "📤 Posição: ainda aberta",
    }

    summaries = {
        "fr": f"✅ *Trade enregistré !*\n\n{side_emoji} {side_label} {data['symbol']}\n📥 Entrée : ${data['entry_price']:,.2f}\n{exit_str['fr']}{pnl_line}\n💵 Montant : ${data['amount']:,.0f}\n🧠 Émotion : {data['emotion']}\n\nUtilise /journal → Post-mortem IA pour analyser tes trades.",
        "en": f"✅ *Trade recorded!*\n\n{side_emoji} {side_label} {data['symbol']}\n📥 Entry: ${data['entry_price']:,.2f}\n{exit_str['en']}{pnl_line}\n💵 Amount: ${data['amount']:,.0f}\n🧠 Emotion: {data['emotion']}\n\nUse /journal → AI Post-mortem to analyze your trades.",
        "es": f"✅ *¡Trade registrado!*\n\n{side_emoji} {side_label} {data['symbol']}\n📥 Entrada: ${data['entry_price']:,.2f}\n{exit_str['es']}{pnl_line}\n💵 Monto: ${data['amount']:,.0f}\n🧠 Emoción: {data['emotion']}\n\nUsa /journal → Post-mortem IA para analizar tus trades.",
        "pt": f"✅ *Trade registrado!*\n\n{side_emoji} {side_label} {data['symbol']}\n📥 Entrada: ${data['entry_price']:,.2f}\n{exit_str['pt']}{pnl_line}\n💵 Valor: ${data['amount']:,.0f}\n🧠 Emoção: {data['emotion']}\n\nUse /journal → Post-mortem IA para analisar seus trades.",
    }
    await message.answer(summaries.get(lang, summaries["fr"]), parse_mode="Markdown")

# ─── Liste des trades ─────────────────────────────────────────────

@router.callback_query(F.data == "journal_list")
async def cb_journal_list(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "fr"
    trades = await get_journal_trades(user_id, limit=10)

    if not trades:
        empty = {"fr": "📭 Aucun trade dans ton journal.\n\nUtilise /journal → Ajouter un trade.", "en": "📭 No trades in your journal.\n\nUse /journal → Add a trade.", "es": "📭 No hay trades en tu diario.", "pt": "📭 Nenhum trade no seu diário."}
        await callback.message.edit_text(empty.get(lang, empty["fr"]))
        await callback.answer()
        return

    titles = {"fr": f"📋 *Tes {len(trades)} derniers trades*\n\n", "en": f"📋 *Your last {len(trades)} trades*\n\n", "es": f"📋 *Tus últimos {len(trades)} trades*\n\n", "pt": f"📋 *Seus últimos {len(trades)} trades*\n\n"}
    lines = [titles.get(lang, titles["fr"])]

    for t in trades:
        side_emoji = "🟢" if t["side"] == "buy" else "🔴"
        pnl_str = ""
        if t["pnl"] is not None:
            pnl_emoji = "🟢" if float(t["pnl"]) >= 0 else "🔴"
            pnl_str = f" | {pnl_emoji} ${float(t['pnl']):+.0f}"
        date_str = t["created_at"].strftime("%d/%m %H:%M")
        lines.append(f"{side_emoji} *{t['symbol']}* ${float(t['entry_price']):,.0f}{pnl_str} — {date_str}")

    await callback.message.edit_text("\n".join(lines), parse_mode="Markdown")
    await callback.answer()

# ─── Post-mortem IA ───────────────────────────────────────────────

@router.callback_query(F.data == "journal_postmortem")
async def cb_journal_postmortem(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "fr"
    trades = await get_journal_trades(user_id, limit=10)

    if not trades:
        empty = {"fr": "📭 Pas encore de trades dans ton journal.", "en": "📭 No trades in your journal yet.", "es": "📭 Aún no hay trades en tu diario.", "pt": "📭 Ainda não há trades no seu diário."}
        await callback.message.edit_text(empty.get(lang, empty["fr"]))
        await callback.answer()
        return

    thinking = {"fr": "🧠 Analyse de tes trades en cours...", "en": "🧠 Analyzing your trades...", "es": "🧠 Analizando tus trades...", "pt": "🧠 Analisando seus trades..."}
    await callback.message.edit_text(thinking.get(lang, thinking["fr"]))

    trades_summary = []
    for t in trades:
        exit_str = f"${float(t['exit_price']):,.2f}" if t["exit_price"] else "ouverte"
        pnl_str = f"{float(t['pnl']):+.2f}$" if t["pnl"] else "N/A"
        trades_summary.append(
            f"- {t['side'].upper()} {t['symbol']} | entrée: ${float(t['entry_price']):,.2f} | sortie: {exit_str} | P&L: {pnl_str} | émotion: {t['emotion']} | raison: {t['reason']}"
        )

    prompts = {
        "fr": (
            f"Voici les {len(trades)} derniers trades de mon journal :\n\n" + "\n".join(trades_summary) +
            f"\n\nProfil : niveau={user.get('level')}, style={user.get('trading_style')}, objectif={user.get('goal')}.\n\n"
            "Génère un post-mortem complet :\n1. Patterns détectés\n2. Biais psychologiques\n3. Statistiques clés\n4. 3 conseils actionnables\nSois direct et constructif."
        ),
        "en": (
            f"Here are my last {len(trades)} journal trades:\n\n" + "\n".join(trades_summary) +
            f"\n\nProfile: level={user.get('level')}, style={user.get('trading_style')}, goal={user.get('goal')}.\n\n"
            "Generate a complete post-mortem:\n1. Detected patterns\n2. Psychological biases\n3. Key statistics\n4. 3 actionable tips\nBe direct and constructive."
        ),
        "es": (
            f"Aquí están mis últimos {len(trades)} trades del diario:\n\n" + "\n".join(trades_summary) +
            f"\n\nPerfil: nivel={user.get('level')}, estilo={user.get('trading_style')}, objetivo={user.get('goal')}.\n\n"
            "Genera un post-mortem completo:\n1. Patrones detectados\n2. Sesgos psicológicos\n3. Estadísticas clave\n4. 3 consejos accionables\nSé directo y constructivo."
        ),
        "pt": (
            f"Aqui estão meus últimos {len(trades)} trades do diário:\n\n" + "\n".join(trades_summary) +
            f"\n\nPerfil: nível={user.get('level')}, estilo={user.get('trading_style')}, objetivo={user.get('goal')}.\n\n"
            "Gere um post-mortem completo:\n1. Padrões detectados\n2. Vieses psicológicos\n3. Estatísticas-chave\n4. 3 dicas acionáveis\nSeja direto e construtivo."
        ),
    }

    analysis = await get_coaching_response(prompts.get(lang, prompts["fr"]), lang, user, [])
    headers = {"fr": f"🧠 *Post-mortem — {len(trades)} trades*\n\n", "en": f"🧠 *Post-mortem — {len(trades)} trades*\n\n", "es": f"🧠 *Post-mortem — {len(trades)} trades*\n\n", "pt": f"🧠 *Post-mortem — {len(trades)} trades*\n\n"}
    await callback.message.edit_text(headers.get(lang, headers["fr"]) + analysis, parse_mode="Markdown")
    await callback.answer()
