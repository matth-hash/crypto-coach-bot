import asyncio
import logging
from datetime import datetime, timezone
from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_users_for_morning_brief, get_all_active_alerts, deactivate_alert
from ai_coach import get_coaching_response
from market_data import get_crypto_prices, get_fear_greed_index, get_market_score

logger = logging.getLogger(__name__)

def format_change(change: float) -> str:
    arrow = "🟢" if change >= 0 else "🔴"
    sign = "+" if change >= 0 else ""
    return f"{arrow} {sign}{change:.1f}%"

def fear_greed_label(score: int) -> str:
    if score <= 20:   return "😱 Peur Extrême"
    if score <= 40:   return "😟 Peur"
    if score <= 60:   return "😐 Neutre"
    if score <= 80:   return "😏 Avidité"
    return "🤑 Avidité Extrême"

# ─── Brief matinal ───────────────────────────────────────────────

async def build_morning_brief(user: dict, prices: dict, fg: dict, market_score: dict) -> str:
    lang = user.get("language", "fr")
    btc = prices.get("BTC", {})
    eth = prices.get("ETH", {})
    sol = prices.get("SOL", {})

    if not btc:
        fallback = {
            "fr": "🌅 Bonjour ! Les données de marché sont temporairement indisponibles. Bonne journée de trading ! 💪",
            "en": "🌅 Good morning! Market data is temporarily unavailable. Happy trading! 💪",
            "es": "🌅 ¡Buenos días! Los datos del mercado no están disponibles. ¡Buen trading! 💪",
            "pt": "🌅 Bom dia! Os dados do mercado estão indisponíveis. Bom trading! 💪",
        }
        return fallback.get(lang, fallback["fr"])

    fg_score = fg["value"]
    fg_lbl = fear_greed_label(fg_score)
    score = market_score.get("score", 50)
    score_label = market_score.get("label", {}).get(lang, "🟡 Neutre")

    prompt_map = {
        "fr": (
            f"Données marché : BTC={btc.get('price', 0):.0f}$ ({btc.get('change_24h', 0):+.1f}%), "
            f"ETH={eth.get('price', 0):.0f}$ ({eth.get('change_24h', 0):+.1f}%), "
            f"Fear&Greed={fg_score}/100, Score marché={score}/100. "
            f"Profil : niveau={user.get('level')}, style={user.get('trading_style')}, objectif={user.get('goal')}. "
            f"Génère un conseil de trading personnalisé en 2-3 phrases. Sois direct et actionnable."
        ),
        "en": (
            f"Market data: BTC={btc.get('price', 0):.0f}$ ({btc.get('change_24h', 0):+.1f}%), "
            f"ETH={eth.get('price', 0):.0f}$ ({eth.get('change_24h', 0):+.1f}%), "
            f"Fear&Greed={fg_score}/100, Market score={score}/100. "
            f"Profile: level={user.get('level')}, style={user.get('trading_style')}, goal={user.get('goal')}. "
            f"Generate a personalized trading tip in 2-3 sentences. Be direct and actionable."
        ),
        "es": (
            f"Datos mercado: BTC={btc.get('price', 0):.0f}$ ({btc.get('change_24h', 0):+.1f}%), "
            f"ETH={eth.get('price', 0):.0f}$ ({eth.get('change_24h', 0):+.1f}%), "
            f"Fear&Greed={fg_score}/100, Score mercado={score}/100. "
            f"Perfil: nivel={user.get('level')}, estilo={user.get('trading_style')}, objetivo={user.get('goal')}. "
            f"Genera un consejo personalizado en 2-3 frases. Sé directo y accionable."
        ),
        "pt": (
            f"Dados mercado: BTC={btc.get('price', 0):.0f}$ ({btc.get('change_24h', 0):+.1f}%), "
            f"ETH={eth.get('price', 0):.0f}$ ({eth.get('change_24h', 0):+.1f}%), "
            f"Fear&Greed={fg_score}/100, Score mercado={score}/100. "
            f"Perfil: nível={user.get('level')}, estilo={user.get('trading_style')}, objetivo={user.get('goal')}. "
            f"Gere uma dica personalizada em 2-3 frases. Seja direto e acionável."
        ),
    }

    try:
        tip = await get_coaching_response(prompt_map.get(lang, prompt_map["fr"]), lang, user, [])
    except Exception:
        tip = ""

    templates = {
        "fr": (
            f"🌅 *Brief du matin*\n\n"
            f"🟡 BTC : ${btc.get('price', 0):,.0f} {format_change(btc.get('change_24h', 0))}\n"
            f"🔵 ETH : ${eth.get('price', 0):,.0f} {format_change(eth.get('change_24h', 0))}\n"
            f"🟣 SOL : ${sol.get('price', 0):,.0f} {format_change(sol.get('change_24h', 0))}\n\n"
            f"😱 Fear & Greed : {fg_score}/100 — {fg_lbl}\n"
            f"📊 Score marché : {score}/100 — {score_label}\n\n"
            f"🧠 *Conseil du jour :*\n{tip}"
        ),
        "en": (
            f"🌅 *Morning Brief*\n\n"
            f"🟡 BTC : ${btc.get('price', 0):,.0f} {format_change(btc.get('change_24h', 0))}\n"
            f"🔵 ETH : ${eth.get('price', 0):,.0f} {format_change(eth.get('change_24h', 0))}\n"
            f"🟣 SOL : ${sol.get('price', 0):,.0f} {format_change(sol.get('change_24h', 0))}\n\n"
            f"😱 Fear & Greed : {fg_score}/100\n"
            f"📊 Market Score : {score}/100 — {score_label}\n\n"
            f"🧠 *Tip of the day :*\n{tip}"
        ),
        "es": (
            f"🌅 *Brief Matutino*\n\n"
            f"🟡 BTC : ${btc.get('price', 0):,.0f} {format_change(btc.get('change_24h', 0))}\n"
            f"🔵 ETH : ${eth.get('price', 0):,.0f} {format_change(eth.get('change_24h', 0))}\n"
            f"🟣 SOL : ${sol.get('price', 0):,.0f} {format_change(sol.get('change_24h', 0))}\n\n"
            f"😱 Fear & Greed : {fg_score}/100\n"
            f"📊 Score mercado : {score}/100 — {score_label}\n\n"
            f"🧠 *Consejo del día :*\n{tip}"
        ),
        "pt": (
            f"🌅 *Brief da manhã*\n\n"
            f"🟡 BTC : ${btc.get('price', 0):,.0f} {format_change(btc.get('change_24h', 0))}\n"
            f"🔵 ETH : ${eth.get('price', 0):,.0f} {format_change(eth.get('change_24h', 0))}\n"
            f"🟣 SOL : ${sol.get('price', 0):,.0f} {format_change(sol.get('change_24h', 0))}\n\n"
            f"😱 Fear & Greed : {fg_score}/100\n"
            f"📊 Score mercado : {score}/100 — {score_label}\n\n"
            f"🧠 *Dica do dia :*\n{tip}"
        ),
    }
    return templates.get(lang, templates["fr"])

# ─── Job : briefs matinaux ───────────────────────────────────────

async def run_morning_briefs(bot: Bot):
    while True:
        try:
            now = datetime.now(timezone.utc).strftime("%H:%M")
            users = await get_users_for_morning_brief(now)
            if users:
                prices, fg, market_score = await asyncio.gather(
                    get_crypto_prices(), get_fear_greed_index(), get_market_score(),
                )
                for user in users:
                    try:
                        brief = await build_morning_brief(user, prices, fg, market_score)
                        await bot.send_message(user["user_id"], brief, parse_mode="Markdown")
                    except Exception as e:
                        logger.error(f"Erreur brief {user['user_id']}: {e}")
        except Exception as e:
            logger.error(f"Erreur run_morning_briefs: {e}")
        await asyncio.sleep(60)

# ─── Job : alertes de prix + rappel journal ──────────────────────

async def run_price_alerts(bot: Bot):
    while True:
        try:
            alerts = await get_all_active_alerts()
            if not alerts:
                await asyncio.sleep(300)
                continue

            prices = await get_crypto_prices()
            if not prices:
                await asyncio.sleep(300)
                continue

            for alert in alerts:
                symbol = alert["symbol"].upper().replace("/USDT", "").replace("/USD", "")
                current_price = prices.get(symbol, {}).get("price")
                if current_price is None:
                    continue

                target = float(alert["target_price"])
                triggered = (
                    alert["condition"] == "above" and current_price >= target
                ) or (
                    alert["condition"] == "below" and current_price <= target
                )

                if triggered:
                    await deactivate_alert(alert["id"])
                    lang = alert.get("language", "fr")
                    direction = ">" if alert["condition"] == "above" else "<"

                    # Message principal
                    messages = {
                        "fr": (
                            f"🔔 *Alerte déclenchée !*\n\n"
                            f"*{symbol}* a atteint ${current_price:,.0f}\n"
                            f"Ton objectif était : {direction} ${target:,.0f}\n\n"
                            f"💡 Analyse la situation avant d'agir.\n\n"
                            f"*Tu as pris le trade ?*"
                        ),
                        "en": (
                            f"🔔 *Alert triggered!*\n\n"
                            f"*{symbol}* reached ${current_price:,.0f}\n"
                            f"Your target was: {direction} ${target:,.0f}\n\n"
                            f"💡 Analyze the situation before acting.\n\n"
                            f"*Did you take the trade?*"
                        ),
                        "es": (
                            f"🔔 *¡Alerta activada!*\n\n"
                            f"*{symbol}* ha alcanzado ${current_price:,.0f}\n"
                            f"Tu objetivo era: {direction} ${target:,.0f}\n\n"
                            f"💡 Analiza la situación antes de actuar.\n\n"
                            f"*¿Tomaste el trade?*"
                        ),
                        "pt": (
                            f"🔔 *Alerta disparado!*\n\n"
                            f"*{symbol}* atingiu ${current_price:,.0f}\n"
                            f"Seu alvo era: {direction} ${target:,.0f}\n\n"
                            f"💡 Analise a situação antes de agir.\n\n"
                            f"*Você entrou no trade?*"
                        ),
                    }

                    # Boutons rappel journal
                    builder = InlineKeyboardBuilder()
                    journal_labels = {
                        "fr": f"📓 Journaliser {symbol}",
                        "en": f"📓 Log {symbol} trade",
                        "es": f"📓 Registrar {symbol}",
                        "pt": f"📓 Registrar {symbol}",
                    }
                    ignore_labels = {
                        "fr": "⏭ Ignorer",
                        "en": "⏭ Skip",
                        "es": "⏭ Ignorar",
                        "pt": "⏭ Ignorar",
                    }
                    builder.button(
                        text=journal_labels.get(lang, journal_labels["fr"]),
                        callback_data=f"alert_journal:{symbol}"
                    )
                    builder.button(
                        text=ignore_labels.get(lang, ignore_labels["fr"]),
                        callback_data="alert_journal_skip"
                    )
                    builder.adjust(1)

                    try:
                        await bot.send_message(
                            alert["user_id"],
                            messages.get(lang, messages["fr"]),
                            reply_markup=builder.as_markup(),
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logger.error(f"Erreur alerte {alert['id']}: {e}")

        except Exception as e:
            logger.error(f"Erreur run_price_alerts: {e}")
        await asyncio.sleep(300)
