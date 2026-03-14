from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import (
    get_user, create_price_alert, save_detected_pattern,
    check_free_limit, increment_daily_usage
)

router = Router()

ASSETS = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOT", "LINK", "MATIC"]
TIMEFRAMES = ["H1", "H4", "D1"]

class PatternScan(StatesGroup):
    waiting_asset = State()
    waiting_timeframe = State()

# ─── Upgrade message helper ───────────────────────────────────────

def _upgrade_msg(lang: str, used: int, limit: int) -> str:
    msgs = {
        "fr": (
            f"⛔ *Limite atteinte* ({used}/{limit} scans aujourd'hui)\n\n"
            f"Le plan gratuit est limité à *{limit} scans de patterns par jour*.\n"
            f"Passe Premium pour des scans illimités ! 🚀\n\n"
            f"/premium — Voir les offres"
        ),
        "en": (
            f"⛔ *Limit reached* ({used}/{limit} scans today)\n\n"
            f"The free plan is limited to *{limit} pattern scans per day*.\n"
            f"Upgrade to Premium for unlimited scans! 🚀\n\n"
            f"/premium — View plans"
        ),
        "es": (
            f"⛔ *Límite alcanzado* ({used}/{limit} scans hoy)\n\n"
            f"El plan gratuito está limitado a *{limit} scans de patrones por día*.\n"
            f"¡Actualiza a Premium para scans ilimitados! 🚀\n\n"
            f"/premium — Ver planes"
        ),
        "pt": (
            f"⛔ *Limite atingido* ({used}/{limit} scans hoje)\n\n"
            f"O plano gratuito é limitado a *{limit} scans de padrões por dia*.\n"
            f"Atualize para Premium para scans ilimitados! 🚀\n\n"
            f"/premium — Ver planos"
        ),
    }
    return msgs.get(lang, msgs["en"])

# ─── /patterns ───────────────────────────────────────────────────

@router.message(Command("patterns"))
async def cmd_patterns(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "fr"

    # Gate freemium
    limit_check = await check_free_limit(user_id, "patterns")
    if not limit_check["allowed"]:
        await message.answer(
            _upgrade_msg(lang, limit_check["used"], limit_check["limit"]),
            parse_mode="Markdown"
        )
        return

    await state.update_data(language=lang)

    builder = InlineKeyboardBuilder()
    for asset in ASSETS:
        builder.button(text=f"🪙 {asset}", callback_data=f"pat_asset:{asset}")
    builder.button(
        text={"fr": "⌨️ Autre", "en": "⌨️ Other", "es": "⌨️ Otro", "pt": "⌨️ Outro"}.get(lang, "⌨️ Other"),
        callback_data="pat_asset:CUSTOM"
    )
    builder.adjust(4)

    # Affiche les scans restants pour les free users
    remaining = limit_check["limit"] - limit_check["used"] if limit_check["limit"] > 0 else "∞"
    remaining_str = {
        "fr": f"\n_Scans restants aujourd'hui : {remaining}_" if limit_check["limit"] > 0 else "",
        "en": f"\n_Scans remaining today: {remaining}_" if limit_check["limit"] > 0 else "",
        "es": f"\n_Scans restantes hoy: {remaining}_" if limit_check["limit"] > 0 else "",
        "pt": f"\n_Scans restantes hoje: {remaining}_" if limit_check["limit"] > 0 else "",
    }.get(lang, "")

    titles = {
        "fr": f"📐 *Analyse de Patterns*\n\nSur quel asset veux-tu scanner les patterns ?{remaining_str}",
        "en": f"📐 *Pattern Analysis*\n\nWhich asset do you want to scan?{remaining_str}",
        "es": f"📐 *Análisis de Patrones*\n\n¿En qué activo quieres escanear patrones?{remaining_str}",
        "pt": f"📐 *Análise de Padrões*\n\nEm qual ativo você quer escanear padrões?{remaining_str}",
    }
    await message.answer(titles.get(lang, titles["fr"]), reply_markup=builder.as_markup(), parse_mode="Markdown")
    await state.set_state(PatternScan.waiting_asset)

@router.callback_query(PatternScan.waiting_asset, F.data.startswith("pat_asset:"))
async def cb_pat_asset(callback: CallbackQuery, state: FSMContext):
    asset = callback.data.split(":")[1]
    data = await state.get_data()
    lang = data.get("language", "fr")

    if asset == "CUSTOM":
        texts = {"fr": "⌨️ Saisis le symbole _(ex: NEAR, INJ, ARB)_ :", "en": "⌨️ Type the symbol _(e.g. NEAR, INJ, ARB)_ :", "es": "⌨️ Escribe el símbolo :", "pt": "⌨️ Digite o símbolo :"}
        await callback.message.edit_text(texts.get(lang, texts["fr"]), parse_mode="Markdown")
        await state.set_state(PatternScan.waiting_timeframe)
        await state.update_data(asset="CUSTOM_PENDING")
        await callback.answer()
        return

    await state.update_data(asset=asset)
    await _ask_timeframe(callback.message, lang, state, edit=True)
    await callback.answer()

@router.message(PatternScan.waiting_asset)
async def process_custom_asset(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("asset") == "CUSTOM_PENDING":
        asset = message.text.strip().upper()[:10]
        await state.update_data(asset=asset)
        lang = data.get("language", "fr")
        await _ask_timeframe(message, lang, state, edit=False)

async def _ask_timeframe(msg, lang, state, edit=False):
    builder = InlineKeyboardBuilder()
    for tf in TIMEFRAMES:
        labels = {"H1": "1 Heure", "H4": "4 Heures", "D1": "Journalier"}
        builder.button(text=f"⏱ {tf} — {labels[tf]}", callback_data=f"pat_tf:{tf}")
    builder.adjust(1)
    texts = {"fr": "⏱ *Timeframe* de l'analyse :", "en": "⏱ *Timeframe* for analysis:", "es": "⏱ *Timeframe* del análisis:", "pt": "⏱ *Timeframe* da análise:"}
    if edit:
        await msg.edit_text(texts.get(lang, texts["fr"]), reply_markup=builder.as_markup(), parse_mode="Markdown")
    else:
        await msg.answer(texts.get(lang, texts["fr"]), reply_markup=builder.as_markup(), parse_mode="Markdown")
    await state.set_state(PatternScan.waiting_timeframe)

@router.callback_query(PatternScan.waiting_timeframe, F.data.startswith("pat_tf:"))
async def cb_pat_timeframe(callback: CallbackQuery, state: FSMContext):
    timeframe = callback.data.split(":")[1]
    data = await state.get_data()
    lang = data.get("language", "fr")
    asset = data.get("asset", "BTC")
    user_id = callback.from_user.id

    loading = {
        "fr": f"🔍 Scan de {asset}/{timeframe} en cours...\n_Récupération des données OHLCV + calcul des indicateurs_",
        "en": f"🔍 Scanning {asset}/{timeframe}...\n_Fetching OHLCV data + computing indicators_",
        "es": f"🔍 Escaneando {asset}/{timeframe}...\n_Obteniendo datos OHLCV + calculando indicadores_",
        "pt": f"🔍 Escaneando {asset}/{timeframe}...\n_Buscando dados OHLCV + calculando indicadores_",
    }
    await callback.message.edit_text(loading.get(lang, loading["fr"]), parse_mode="Markdown")
    await state.clear()

    # Incrément compteur avant le scan
    await increment_daily_usage(user_id, "patterns")

    from patterns_engine import analyze_asset
    result = await analyze_asset(asset, timeframe)

    if not result:
        errors = {
            "fr": f"❌ Impossible de récupérer les données pour {asset}.\nVérifie que le symbole est disponible.",
            "en": f"❌ Unable to fetch data for {asset}.\nCheck that the symbol is available.",
            "es": f"❌ No se pueden obtener datos para {asset}.",
            "pt": f"❌ Não foi possível obter dados para {asset}.",
        }
        await callback.message.edit_text(errors.get(lang, errors["fr"]))
        await callback.answer()
        return

    try:
        await save_detected_pattern(
            user_id=user_id,
            symbol=asset,
            timeframe=timeframe,
            pattern_name=result["pattern"]["name"],
            pattern_type=result["pattern"]["type"],
            stars=result["stars"],
            neckline=result["pattern"].get("neckline"),
            target=result["pattern"].get("target"),
        )
    except Exception:
        pass

    text = _format_result(result, lang)
    builder = _build_alert_keyboard(result, lang)
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()

# ─── Formatage du résultat ────────────────────────────────────────

def _format_result(result: dict, lang: str) -> str:
    pattern = result["pattern"]
    stars = "⭐" * result["stars"] + "☆" * (5 - result["stars"])
    rsi = result["rsi"]
    macd = result["macd"]
    fib = result["fib"]
    vol_ratio = result["vol_ratio"]
    multitf = result["multitf"]
    current = result["current_price"]
    symbol = result["symbol"]
    timeframe = result["timeframe"]

    if rsi < 30:        rsi_label = "🟢 Survente" if lang == "fr" else "🟢 Oversold"
    elif rsi > 70:      rsi_label = "🔴 Surachat" if lang == "fr" else "🔴 Overbought"
    else:               rsi_label = "😐 Neutre" if lang == "fr" else "😐 Neutral"

    macd_cross_labels = {
        "bullish": {"fr": "🟢 Croisement haussier", "en": "🟢 Bullish cross", "es": "🟢 Cruce alcista", "pt": "🟢 Cruzamento altista"},
        "bearish": {"fr": "🔴 Croisement baissier", "en": "🔴 Bearish cross", "es": "🔴 Cruce bajista", "pt": "🔴 Cruzamento baixista"},
        "neutral": {"fr": "😐 Neutre", "en": "😐 Neutral", "es": "😐 Neutral", "pt": "😐 Neutro"},
    }
    macd_label = macd_cross_labels.get(macd["cross"], macd_cross_labels["neutral"]).get(lang, "😐 Neutral")
    type_emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}.get(pattern["type"], "🟡")

    mtf_line = ""
    if multitf:
        mtf_line = "\n" + {"fr": "⚠️ Signal confirmé sur timeframe supérieur !", "en": "⚠️ Signal confirmed on higher timeframe!", "es": "⚠️ ¡Señal confirmada en timeframe superior!", "pt": "⚠️ Sinal confirmado no timeframe superior!"}.get(lang, "⚠️ Multi-TF confirmed!")

    neckline = pattern.get("neckline")
    target = pattern.get("target")
    neckline_line = f"\n📍 Neckline : ${neckline:,.2f}" if neckline else ""
    target_line = f"\n🎯 Cible : ${target:,.2f}" if target else ""

    fib_line = (
        f"\n\n📏 *Fibonacci*\n"
        f"• 0.382 : ${fib['0.382']:,.2f}\n"
        f"• 0.500 : ${fib['0.500']:,.2f}\n"
        f"• 0.618 : ${fib['0.618']:,.2f}"
    )

    support = pattern.get("support")
    resistance = pattern.get("resistance")
    sr_line = ""
    if support and resistance:
        sr_line = f"\n🛡 Support : ${support:,.2f} | 📊 Résistance : ${resistance:,.2f}"

    # Disclaimer
    disclaimer = {
        "fr": "\n\n_⚠️ Signal technique uniquement. Confirme toujours avec le contexte macro._",
        "en": "\n\n_⚠️ Technical signal only. Always confirm with macro context._",
        "es": "\n\n_⚠️ Solo señal técnica. Confirma siempre con el contexto macro._",
        "pt": "\n\n_⚠️ Apenas sinal técnico. Sempre confirme com o contexto macro._",
    }

    titles = {
        "fr": f"📐 *{pattern['name']}* — {symbol}/{timeframe}\n{type_emoji} Signal {pattern['type']}",
        "en": f"📐 *{pattern['name']}* — {symbol}/{timeframe}\n{type_emoji} {pattern['type'].capitalize()} signal",
        "es": f"📐 *{pattern['name']}* — {symbol}/{timeframe}\n{type_emoji} Señal {pattern['type']}",
        "pt": f"📐 *{pattern['name']}* — {symbol}/{timeframe}\n{type_emoji} Sinal {pattern['type']}",
    }

    return (
        f"{titles.get(lang, titles['fr'])}\n"
        f"{stars} — {result['stars']}/5\n"
        f"\n💰 Prix actuel : ${current:,.2f}"
        f"{neckline_line}{target_line}{sr_line}"
        f"\n\n📊 *Indicateurs*\n"
        f"• RSI 14 : {rsi} — {rsi_label}\n"
        f"• MACD : {macd_label}\n"
        f"• Volume : {vol_ratio:.1f}x la moyenne"
        f"{mtf_line}{fib_line}"
        f"{disclaimer.get(lang, disclaimer['en'])}"
    )

def _build_alert_keyboard(result: dict, lang: str):
    pattern = result["pattern"]
    builder = InlineKeyboardBuilder()
    alert_price = pattern.get("alert_price")
    alert_condition = pattern.get("alert_condition", "above")
    symbol = result["symbol"]

    if alert_price:
        direction = ">" if alert_condition == "above" else "<"
        alert_labels = {
            "fr": f"🔔 Créer une alerte si {symbol} {direction} ${alert_price:,.0f}",
            "en": f"🔔 Create alert if {symbol} {direction} ${alert_price:,.0f}",
            "es": f"🔔 Crear alerta si {symbol} {direction} ${alert_price:,.0f}",
            "pt": f"🔔 Criar alerta se {symbol} {direction} ${alert_price:,.0f}",
        }
        builder.button(
            text=alert_labels.get(lang, alert_labels["fr"]),
            callback_data=f"pat_alert:{symbol}:{alert_condition}:{alert_price}"
        )

    scan_again = {"fr": "🔄 Nouveau scan", "en": "🔄 New scan", "es": "🔄 Nuevo scan", "pt": "🔄 Novo scan"}
    builder.button(text=scan_again.get(lang, scan_again["fr"]), callback_data="pat_restart")
    builder.adjust(1)
    return builder

# ─── Création alerte depuis pattern ──────────────────────────────

@router.callback_query(F.data.startswith("pat_alert:"))
async def cb_pat_alert(callback: CallbackQuery):
    _, symbol, condition, price_str = callback.data.split(":")
    user_id = callback.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "fr"

    # Gate freemium alertes
    limit_check = await check_free_limit(user_id, "alerts")
    if not limit_check["allowed"]:
        from bot.alerts_handlers import _upgrade_msg
        await callback.message.edit_text(
            _upgrade_msg(lang, limit_check["used"], limit_check["limit"]),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    try:
        target_price = float(price_str)
        await create_price_alert(user_id, symbol, condition, target_price)
        direction = ">" if condition == "above" else "<"
        success = {
            "fr": f"✅ *Alerte créée !*\n\n🔔 Tu seras notifié si {symbol} {direction} ${target_price:,.0f}\n\nGère tes alertes avec /alertes",
            "en": f"✅ *Alert created!*\n\n🔔 You'll be notified if {symbol} {direction} ${target_price:,.0f}\n\nManage alerts with /alertes",
            "es": f"✅ *¡Alerta creada!*\n\n🔔 Serás notificado si {symbol} {direction} ${target_price:,.0f}\n\nGestiona tus alertas con /alertes",
            "pt": f"✅ *Alerta criado!*\n\n🔔 Você será notificado se {symbol} {direction} ${target_price:,.0f}\n\nGerencie alertas com /alertes",
        }
        await callback.message.edit_text(success.get(lang, success["fr"]), parse_mode="Markdown")
    except Exception as e:
        await callback.message.edit_text(f"❌ Erreur création alerte: {e}")
    await callback.answer()

@router.callback_query(F.data == "pat_restart")
async def cb_pat_restart(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "fr"

    limit_check = await check_free_limit(user_id, "patterns")
    if not limit_check["allowed"]:
        await callback.message.edit_text(
            _upgrade_msg(lang, limit_check["used"], limit_check["limit"]),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    await state.update_data(language=lang)
    builder = InlineKeyboardBuilder()
    for asset in ASSETS:
        builder.button(text=f"🪙 {asset}", callback_data=f"pat_asset:{asset}")
    builder.button(text="⌨️ Autre", callback_data="pat_asset:CUSTOM")
    builder.adjust(4)

    titles = {
        "fr": "📐 *Analyse de Patterns*\n\nSur quel asset ?",
        "en": "📐 *Pattern Analysis*\n\nWhich asset?",
        "es": "📐 *Análisis de Patrones*\n\n¿En qué activo?",
        "pt": "📐 *Análise de Padrões*\n\nEm qual ativo?",
    }
    await callback.message.edit_text(titles.get(lang, titles["fr"]), reply_markup=builder.as_markup(), parse_mode="Markdown")
    await state.set_state(PatternScan.waiting_asset)
    await callback.answer()
