from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import (
    get_user, save_journal_trade, get_journal_trades,
    save_postmortem, delete_journal_trade, update_xp
)
from ai_coach import get_coaching_response

router = Router()

SYMBOLS = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AUTRE"]

EMOTIONS = {
    "fr": [
        ("😰 FOMO", "fomo"),
        ("😎 Confiant", "confident"),
        ("😰 Stressé", "stressed"),
        ("😐 Neutre", "neutral"),
        ("🤑 Avidité", "greed"),
    ],
    "en": [
        ("😰 FOMO", "fomo"),
        ("😎 Confident", "confident"),
        ("😰 Stressed", "stressed"),
        ("😐 Neutral", "neutral"),
        ("🤑 Greed", "greed"),
    ],
    "es": [
        ("😰 FOMO", "fomo"),
        ("😎 Confiado", "confident"),
        ("😰 Estresado", "stressed"),
        ("😐 Neutral", "neutral"),
        ("🤑 Avaricia", "greed"),
    ],
    "pt": [
        ("😰 FOMO", "fomo"),
        ("😎 Confiante", "confident"),
        ("😰 Estressado", "stressed"),
        ("😐 Neutro", "neutral"),
        ("🤑 Ganância", "greed"),
    ],
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
    builder.button(text="➕ Ajouter un trade" if lang == "fr" else "➕ Add a trade", callback_data="journal_add")
    builder.button(text="📋 Mes trades" if lang == "fr" else "📋 My trades", callback_data="journal_list")
    builder.button(text="🧠 Post-mortem IA" if lang == "fr" else "🧠 AI Post-mortem", callback_data="journal_postmortem")
    builder.adjust(1)

    titles = {
        "fr": "📓 *Journal de Trading*\n\nEnregistre tes trades avec leur contexte émotionnel et obtiens une analyse IA personnalisée.",
        "en": "📓 *Trading Journal*\n\nRecord your trades with emotional context and get personalized AI analysis.",
        "es": "📓 *Diario de Trading*\n\nRegistra tus operaciones con contexto emocional y obtén análisis IA personalizado.",
        "pt": "📓 *Diário de Trading*\n\nRegistre seus trades com contexto emocional e obtenha análise IA personalizada.",
    }
    await message.answer(
        titles.get(lang, titles["fr"]),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

# ─── Ajouter un trade ────────────────────────────────────────────

@router.callback_query(F.data == "journal_add")
async def cb_journal_add(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "fr")

    builder = InlineKeyboardBuilder()
    for symbol in SYMBOLS:
        builder.button(text=f"🪙 {symbol}", callback_data=f"journal_symbol:{symbol}")
    builder.adjust(4)

    texts = {
        "fr": "🪙 *Nouveau trade*\n\nSur quelle crypto ?",
        "en": "🪙 *New trade*\n\nWhich crypto?",
        "es": "🪙 *Nuevo trade*\n\n¿En qué cripto?",
        "pt": "🪙 *Novo trade*\n\nEm qual cripto?",
    }
    await callback.message.edit_text(
        texts.get(lang, texts["fr"]),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(JournalSetup.waiting_symbol)
    await callback.answer()

@router.callback_query(JournalSetup.waiting_symbol, F.data.startswith("journal_symbol:"))
async def cb_journal_symbol(callback: CallbackQuery, state: FSMContext):
    symbol = callback.data.split(":")[1]
    data = await state.get_data()
    lang = data.get("language", "fr")

    if symbol == "AUTRE":
        texts = {
            "fr": "⌨️ Saisis le symbole de ta crypto _(ex: MATIC, LINK, DOT)_ :",
            "en": "⌨️ Type your crypto symbol _(e.g. MATIC, LINK, DOT)_ :",
            "es": "⌨️ Escribe el símbolo de tu cripto _(ej: MATIC, LINK, DOT)_ :",
            "pt": "⌨️ Digite o símbolo da sua cripto _(ex: MATIC, LINK, DOT)_ :",
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

    texts = {
        "fr": "📊 Direction du trade :",
        "en": "📊 Trade direction:",
        "es": "📊 Dirección del trade:",
        "pt": "📊 Direção do trade:",
    }
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

    texts = {
        "fr": "💰 *Prix d'entrée* en $ _(ex: 65000)_ :",
        "en": "💰 *Entry price* in $ _(e.g. 65000)_ :",
        "es": "💰 *Precio de entrada* en $ _(ej: 65000)_ :",
        "pt": "💰 *Preço de entrada* em $ _(ex: 65000)_ :",
    }
    await callback.message.edit_text(texts.get(lang, texts["fr"]), parse_mode="Markdown")
    await state.set_state(JournalSetup.waiting_entry_price)
    await callback.answer()

@router.message(JournalSetup.waiting_entry_price)
async def process_entry_price(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "fr")

    try:
        price = float(message.text.strip().replace(",", ".").replace(" ", ""))
        if price <= 0:
            raise ValueError
    except ValueError:
        errors = {
            "fr": "❌ Prix invalide. Ex: *65000* ou *2500.50*",
            "en": "❌ Invalid price. E.g.: *65000* or *2500.50*",
            "es": "❌ Precio inválido. Ej: *65000* o *2500.50*",
            "pt": "❌ Preço inválido. Ex: *65000* ou *2500.50*",
        }
        await message.answer(errors.get(lang, errors["fr"]), parse_mode="Markdown")
        return

    await state.update_data(entry_price=price)

    builder = InlineKeyboardBuilder()
    skip_labels = {
        "fr": "⏭ Position encore ouverte",
        "en": "⏭ Position still open",
        "es": "⏭ Posición aún abierta",
        "pt": "⏭ Posição ainda aberta",
    }
    builder.button(text=skip_labels.get(lang, skip_labels["fr"]), callback_data="journal_exit_skip")

    texts = {
        "fr": "💰 *Prix de sortie* en $ _(ou ignore si position ouverte)_ :",
        "en": "💰 *Exit price* in $ _(or skip if position still open)_ :",
        "es": "💰 *Precio de salida* en $ _(o ignora si posición abierta)_ :",
        "pt": "💰 *Preço de saída* em $ _(ou ignore se posição ainda aberta)_ :",
    }
    await message.answer(
        texts.get(lang, texts["fr"]),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
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
        if price <= 0:
            raise ValueError
    except ValueError:
        errors = {
            "fr": "❌ Prix invalide. Ex: *68000*",
            "en": "❌ Invalid price. E.g.: *68000*",
            "es": "❌ Precio inválido. Ej: *68000*",
            "pt": "❌ Preço inválido. Ex: *68000*",
        }
        await message.answer(errors.get(lang, errors["fr"]), parse_mode="Markdown")
        return

    await state.update_data(exit_price=price)
    await _ask_amount(message, lang, state, edit=False)

async def _ask_amount(msg, lang, state, edit=False):
    texts = {
        "fr": "📦 *Montant investi* en $ _(ex: 500)_ :",
        "en": "📦 *Amount invested* in $ _(e.g. 500)_ :",
        "es": "📦 *Monto invertido* en $ _(ej: 500)_ :",
        "pt": "📦 *Valor investido* em $ _(ex: 500)_ :",
    }
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
        if amount <= 0:
            raise ValueError
    except ValueError:
        errors = {
            "fr": "❌ Montant invalide. Ex: *500*",
            "en": "❌ Invalid amount. E.g.: *500*",
            "es": "❌ Monto inválido. Ej: *500*",
            "pt": "❌ Valor inválido. Ex: *500*",
        }
        await message.answer(errors.get(lang, errors["fr"]), parse_mode="Markdown")
        return

    await state.update_data(amount=amount)

    builder = InlineKeyboardBuilder()
    for label, val in EMOTIONS.get(lang, EMOTIONS["fr"]):
        builder.button(text=label, callback_data=f"journal_emotion:{val}")
    builder.adjust(2)

    texts = {
        "fr": "🧠 *État émotionnel* au moment du trade :",
        "en": "🧠 *Emotional state* at the time of the trade:",
        "es": "🧠 *Estado emocional* en el momento del trade:",
        "pt": "🧠 *Estado emocional* no momento do trade:",
    }
    await message.answer(
        texts.get(lang, texts["fr"]),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(JournalSetup.waiting_emotion)

@router.callback_query(JournalSetup.waiting_emotion, F.data.startswith("journal_emotion:"))
async def cb_journal_emotion(callback: CallbackQuery, state: FSMContext):
    emotion = callback.data.split(":")[1]
    data = await state.get_data()
    lang = data.get("language", "fr")

    await state.update_data(emotion=emotion)
    await callback.message.edit_reply_markup()

    texts = {
        "fr": "✍️ *Raison du trade* — pourquoi tu as pris cette position ? _(1-2 phrases)_",
        "en": "✍️ *Trade reason* — why did you take this position? _(1-2 sentences)_",
        "es": "✍️ *Razón del trade* — ¿por qué tomaste esta posición? _(1-2 frases)_",
        "pt": "✍️ *Motivo do trade* — por que você tomou essa posição? _(1-2 frases)_",
    }
    await callback.message.answer(texts.get(lang, texts["fr"]), parse_mode="Markdown")
    await state.set_state(JournalSetup.waiting_reason)
    await callback.answer()

@router.message(JournalSetup.waiting_reason)
async def process_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "fr")
    reason = message.text.strip()[:500]

    user_id = message.from_user.id
    trade_id = await save_journal_trade(
        user_id=user_id,
        symbol=data["symbol"],
        side=data["side"],
        entry_price=data["entry_price"],
        exit_price=data.get("exit_price"),
        amount=data["amount"],
        emotion=data["emotion"],
        reason=reason,
    )
    await update_xp(user_id, 10)
    await state.clear()

    # Résumé du trade
    exit_price = data.get("exit_price")
    side_emoji = "🟢" if data["side"] == "buy" else "🔴"
    side_label = {"fr": "ACHAT", "en": "BUY", "es": "COMPRA", "pt": "COMPRA"}.get(lang, "BUY") if data["side"] == "buy" else {"fr": "VENTE", "en": "SELL", "es": "VENTA", "pt": "VENDA"}.get(lang, "SELL")

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

    summaries = {
        "fr": (
            f"✅ *Trade enregistré !*\n\n"
            f"{side_emoji} {side_label} {data['symbol']}\n"
            f"📥 Entrée : ${data['entry_price']:,.2f}\n"
            f"{'📤 Sortie : $' + f\"{exit_price:,.2f}\" if exit_price else '📤 Position : encore ouverte'}"
            f"{pnl_line}\n"
            f"💵 Montant : ${data['amount']:,.0f}\n"
            f"🧠 Émotion : {data['emotion']}\n\n"
            f"Utilise /journal → Post-mortem IA pour analyser tes trades."
        ),
        "en": (
            f"✅ *Trade recorded!*\n\n"
            f"{side_emoji} {side_label} {data['symbol']}\n"
            f"📥 Entry: ${data['entry_price']:,.2f}\n"
            f"{'📤 Exit: $' + f\"{exit_price:,.2f}\" if exit_price else '📤 Position: still open'}"
            f"{pnl_line}\n"
            f"💵 Amount: ${data['amount']:,.0f}\n"
            f"🧠 Emotion: {data['emotion']}\n\n"
            f"Use /journal → AI Post-mortem to analyze your trades."
        ),
        "es": (
            f"✅ *¡Trade registrado!*\n\n"
            f"{side_emoji} {side_label} {data['symbol']}\n"
            f"📥 Entrada: ${data['entry_price']:,.2f}\n"
            f"{'📤 Salida: $' + f\"{exit_price:,.2f}\" if exit_price else '📤 Posición: aún abierta'}"
            f"{pnl_line}\n"
            f"💵 Monto: ${data['amount']:,.0f}\n"
            f"🧠 Emoción: {data['emotion']}\n\n"
            f"Usa /journal → Post-mortem IA para analizar tus trades."
        ),
        "pt": (
            f"✅ *Trade registrado!*\n\n"
            f"{side_emoji} {side_label} {data['symbol']}\n"
            f"📥 Entrada: ${data['entry_price']:,.2f}\n"
            f"{'📤 Saída: $' + f\"{exit_price:,.2f}\" if exit_price else '📤 Posição: ainda aberta'}"
            f"{pnl_line}\n"
            f"💵 Valor: ${data['amount']:,.0f}\n"
            f"🧠 Emoção: {data['emotion']}\n\n"
            f"Use /journal → Post-mortem IA para analisar seus trades."
        ),
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
        empty = {
            "fr": "📭 Aucun trade dans ton journal.\n\nUtilise /journal → Ajouter un trade.",
            "en": "📭 No trades in your journal.\n\nUse /journal → Add a trade.",
            "es": "📭 No hay trades en tu diario.\n\nUsa /journal → Agregar un trade.",
            "pt": "📭 Nenhum trade no seu diário.\n\nUse /journal → Adicionar um trade.",
        }
        await callback.message.edit_text(empty.get(lang, empty["fr"]))
        await callback.answer()
        return

    lines = []
    titles = {
        "fr": f"📋 *Tes {len(trades)} derniers trades*\n\n",
        "en": f"📋 *Your last {len(trades)} trades*\n\n",
        "es": f"📋 *Tus últimos {len(trades)} trades*\n\n",
        "pt": f"📋 *Seus últimos {len(trades)} trades*\n\n",
    }
    lines.append(titles.get(lang, titles["fr"]))

    for t in trades:
        side_emoji = "🟢" if t["side"] == "buy" else "🔴"
        pnl_str = ""
        if t["pnl"] is not None:
            pnl_emoji = "🟢" if float(t["pnl"]) >= 0 else "🔴"
            pnl_str = f" | {pnl_emoji} ${float(t['pnl']):+.0f}"
        date_str = t["created_at"].strftime("%d/%m %H:%M")
        lines.append(f"{side_emoji} *{t['symbol']}* ${float(t['entry_price']):,.0f}{pnl_str} — {date_str}")

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="Markdown"
    )
    await callback.answer()

# ─── Post-mortem IA ───────────────────────────────────────────────

@router.callback_query(F.data == "journal_postmortem")
async def cb_journal_postmortem(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "fr"

    trades = await get_journal_trades(user_id, limit=10)

    if not trades:
        empty = {
            "fr": "📭 Pas encore de trades dans ton journal.\n\nEnregistre au moins un trade pour obtenir une analyse.",
            "en": "📭 No trades in your journal yet.\n\nRecord at least one trade to get analysis.",
            "es": "📭 Aún no hay trades en tu diario.\n\nRegistra al menos un trade para obtener análisis.",
            "pt": "📭 Ainda não há trades no seu diário.\n\nRegistre pelo menos um trade para obter análise.",
        }
        await callback.message.edit_text(empty.get(lang, empty["fr"]))
        await callback.answer()
        return

    thinking = {
        "fr": "🧠 Analyse de tes trades en cours...",
        "en": "🧠 Analyzing your trades...",
        "es": "🧠 Analizando tus trades...",
        "pt": "🧠 Analisando seus trades...",
    }
    await callback.message.edit_text(thinking.get(lang, thinking["fr"]))

    # Construction du résumé pour l'IA
    trades_summary = []
    for t in trades:
        exit_str = f"${float(t['exit_price']):,.2f}" if t["exit_price"] else "ouverte"
        pnl_str = f"{float(t['pnl']):+.2f}$" if t["pnl"] else "N/A"
        trades_summary.append(
            f"- {t['side'].upper()} {t['symbol']} | entrée: ${float(t['entry_price']):,.2f} "
            f"| sortie: {exit_str} | P&L: {pnl_str} | émotion: {t['emotion']} | raison: {t['reason']}"
        )

    prompts = {
        "fr": (
            f"Voici les {len(trades)} derniers trades de mon journal :\n\n"
            + "\n".join(trades_summary)
            + f"\n\nMon profil : niveau={user.get('level')}, style={user.get('trading_style')}, objectif={user.get('goal')}.\n\n"
            "Génère un post-mortem complet :\n"
            "1. Patterns détectés (positifs et négatifs)\n"
            "2. Biais psychologiques identifiés\n"
            "3. Statistiques clés (win rate, P&L total si dispo)\n"
            "4. 3 conseils actionnables et personnalisés\n"
            "Sois direct, précis et constructif."
        ),
        "en": (
            f"Here are my last {len(trades)} journal trades:\n\n"
            + "\n".join(trades_summary)
            + f"\n\nMy profile: level={user.get('level')}, style={user.get('trading_style')}, goal={user.get('goal')}.\n\n"
            "Generate a complete post-mortem:\n"
            "1. Detected patterns (positive and negative)\n"
            "2. Identified psychological biases\n"
            "3. Key statistics (win rate, total P&L if available)\n"
            "4. 3 actionable personalized tips\n"
            "Be direct, precise and constructive."
        ),
        "es": (
            f"Aquí están mis últimos {len(trades)} trades del diario:\n\n"
            + "\n".join(trades_summary)
            + f"\n\nMi perfil: nivel={user.get('level')}, estilo={user.get('trading_style')}, objetivo={user.get('goal')}.\n\n"
            "Genera un post-mortem completo:\n"
            "1. Patrones detectados (positivos y negativos)\n"
            "2. Sesgos psicológicos identificados\n"
            "3. Estadísticas clave (win rate, P&L total si disponible)\n"
            "4. 3 consejos accionables y personalizados\n"
            "Sé directo, preciso y constructivo."
        ),
        "pt": (
            f"Aqui estão meus últimos {len(trades)} trades do diário:\n\n"
            + "\n".join(trades_summary)
            + f"\n\nMeu perfil: nível={user.get('level')}, estilo={user.get('trading_style')}, objetivo={user.get('goal')}.\n\n"
            "Gere um post-mortem completo:\n"
            "1. Padrões detectados (positivos e negativos)\n"
            "2. Vieses psicológicos identificados\n"
            "3. Estatísticas-chave (win rate, P&L total se disponível)\n"
            "4. 3 dicas acionáveis e personalizadas\n"
            "Seja direto, preciso e construtivo."
        ),
    }

    analysis = await get_coaching_response(
        prompts.get(lang, prompts["fr"]), lang, user, []
    )

    headers = {
        "fr": f"🧠 *Post-mortem — {len(trades)} trades analysés*\n\n",
        "en": f"🧠 *Post-mortem — {len(trades)} trades analyzed*\n\n",
        "es": f"🧠 *Post-mortem — {len(trades)} trades analizados*\n\n",
        "pt": f"🧠 *Post-mortem — {len(trades)} trades analisados*\n\n",
    }

    await callback.message.edit_text(
        headers.get(lang, headers["fr"]) + analysis,
        parse_mode="Markdown"
    )
    await callback.answer()
