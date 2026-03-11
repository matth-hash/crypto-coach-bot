import asyncio
import logging
from datetime import datetime, timezone
from aiogram import Bot
from pycoingecko import CoinGeckoAPI
from database import get_users_for_morning_brief, get_all_active_alerts, deactivate_alert
from ai_coach import get_coaching_response

logger = logging.getLogger(__name__)
cg = CoinGeckoAPI()

# ─── Données de marché ───────────────────────────────────────────

async def fetch_market_data() -> dict:
    """Récupère BTC, ETH, SOL et Fear & Greed via CoinGecko."""
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: cg.get_price(
            ids=["bitcoin", "ethereum", "solana"],
            vs_currencies=["usd"],
            include_24hr_change=True
        ))
        fg = await loop.run_in_executor(None, lambda: cg.get_global())

        btc = data.get("bitcoin", {})
        eth = data.get("ethereum", {})
        sol = data.get("solana", {})

        # Fear & Greed approximé via market_cap_change_percentage_24h_usd
        market_change = fg.get("data", {}).get("market_cap_change_percentage_24h_usd", 0)
        fear_greed = max(0, min(100, int(50 + market_change * 2)))

        return {
            "btc_price": btc.get("usd", 0),
            "btc_change": btc.get("usd_24h_change", 0),
            "eth_price": eth.get("usd", 0),
            "eth_change": eth.get("usd_24h_change", 0),
            "sol_price": sol.get("usd", 0),
            "sol_change": sol.get("usd_24h_change", 0),
            "fear_greed": fear_greed,
        }
    except Exception as e:
        logger.error(f"Erreur fetch_market_data: {e}")
        return {}

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

# ─── Message de brief matin ─────────────────────────────────────

async def build_morning_brief(user: dict, market: dict) -> str:
    """Construit le brief personnalisé selon le profil utilisateur."""
    lang = user.get("language", "fr")

    if not market:
        fallback = {
            "fr": "🌅 Bonjour ! Les données de marché sont temporairement indisponibles. Bonne journée de trading ! 💪",
            "en": "🌅 Good morning! Market data is temporarily unavailable. Happy trading! 💪",
            "es": "🌅 ¡Buenos días! Los datos del mercado no están disponibles temporalmente. ¡Buen trading! 💪",
            "pt": "🌅 Bom dia! Os dados do mercado estão temporariamente indisponíveis. Bom trading! 💪",
        }
        return fallback.get(lang, fallback["fr"])

    fg_score = market["fear_greed"]
    fg_label = fear_greed_label(fg_score)

    # Prompt IA pour conseil personnalisé
    prompt_map = {
        "fr": (
            f"Données marché du jour : BTC={market['btc_price']:.0f}$ ({market['btc_change']:+.1f}%), "
            f"ETH={market['eth_price']:.0f}$ ({market['eth_change']:+.1f}%), "
            f"Fear&Greed={fg_score}/100. "
            f"Profil trader : niveau={user.get('level')}, style={user.get('trading_style')}, objectif={user.get('goal')}. "
            f"Génère un conseil de trading personnalisé en 2-3 phrases maximum. Sois direct et actionnable."
        ),
        "en": (
            f"Market data: BTC={market['btc_price']:.0f}$ ({market['btc_change']:+.1f}%), "
            f"ETH={market['eth_price']:.0f}$ ({market['eth_change']:+.1f}%), "
            f"Fear&Greed={fg_score}/100. "
            f"Trader profile: level={user.get('level')}, style={user.get('trading_style')}, goal={user.get('goal')}. "
            f"Generate a personalized trading tip in 2-3 sentences max. Be direct and actionable."
        ),
        "es": (
            f"Datos del mercado: BTC={market['btc_price']:.0f}$ ({market['btc_change']:+.1f}%), "
            f"ETH={market['eth_price']:.0f}$ ({market['eth_change']:+.1f}%), "
            f"Fear&Greed={fg_score}/100. "
            f"Perfil trader: nivel={user.get('level')}, estilo={user.get('trading_style')}, objetivo={user.get('goal')}. "
            f"Genera un consejo de trading personalizado en 2-3 frases máximo. Sé directo y accionable."
        ),
        "pt": (
            f"Dados do mercado: BTC={market['btc_price']:.0f}$ ({market['btc_change']:+.1f}%), "
            f"ETH={market['eth_price']:.0f}$ ({market['eth_change']:+.1f}%), "
            f"Fear&Greed={fg_score}/100. "
            f"Perfil trader: nível={user.get('level')}, estilo={user.get('trading_style')}, objetivo={user.get('goal')}. "
            f"Gere uma dica de trading personalizada em 2-3 frases máximo. Seja direto e acionável."
        ),
    }

    try:
        tip = await get_coaching_response(
            prompt_map.get(lang, prompt_map["fr"]), lang, user, []
        )
    except Exception:
        tip = ""

    templates = {
        "fr": (
            f"🌅 *Brief du matin*\n\n"
            f"🟡 BTC : ${market['btc_price']:,.0f} {format_change(market['btc_change'])}\n"
            f"🔵 ETH : ${market['eth_price']:,.0f} {format_change(market['eth_change'])}\n"
            f"🟣 SOL : ${market['sol_price']:,.0f} {format_change(market['sol_change'])}\n\n"
            f"😱 Fear & Greed : {fg_score}/100 — {fg_label}\n\n"
            f"🧠 *Conseil du jour :*\n{tip}"
        ),
        "en": (
            f"🌅 *Morning Brief*\n\n"
            f"🟡 BTC : ${market['btc_price']:,.0f} {format_change(market['btc_change'])}\n"
            f"🔵 ETH : ${market['eth_price']:,.0f} {format_change(market['eth_change'])}\n"
            f"🟣 SOL : ${market['sol_price']:,.0f} {format_change(market['sol_change'])}\n\n"
            f"😱 Fear & Greed : {fg_score}/100 — {fg_label}\n\n"
            f"🧠 *Tip of the day :*\n{tip}"
        ),
        "es": (
            f"🌅 *Brief matutino*\n\n"
            f"🟡 BTC : ${market['btc_price']:,.0f} {format_change(market['btc_change'])}\n"
            f"🔵 ETH : ${market['eth_price']:,.0f} {format_change(market['eth_change'])}\n"
            f"🟣 SOL : ${market['sol_price']:,.0f} {format_change(market['sol_change'])}\n\n"
            f"😱 Fear & Greed : {fg_score}/100 — {fg_label}\n\n"
            f"🧠 *Consejo del día :*\n{tip}"
        ),
        "pt": (
            f"🌅 *Brief da manhã*\n\n"
            f"🟡 BTC : ${market['btc_price']:,.0f} {format_change(market['btc_change'])}\n"
            f"🔵 ETH : ${market['eth_price']:,.0f} {format_change(market['eth_change'])}\n"
            f"🟣 SOL : ${market['sol_price']:,.0f} {format_change(market['sol_change'])}\n\n"
            f"😱 Fear & Greed : {fg_score}/100 — {fg_label}\n\n"
            f"🧠 *Dica do dia :*\n{tip}"
        ),
    }
    return templates.get(lang, templates["fr"])

# ─── Job : briefs matinaux ───────────────────────────────────────

async def run_morning_briefs(bot: Bot):
    """Tourne toutes les minutes, envoie les briefs à l'heure configurée."""
    while True:
        try:
            now = datetime.now(timezone.utc).strftime("%H:%M")
            users = await get_users_for_morning_brief(now)

            if users:
                market = await fetch_market_data()
                for user in users:
                    try:
                        brief = await build_morning_brief(user, market)
                        await bot.send_message(
                            user["user_id"], brief, parse_mode="Markdown"
                        )
                        logger.info(f"Brief envoyé à {user['user_id']}")
                    except Exception as e:
                        logger.error(f"Erreur envoi brief {user['user_id']}: {e}")

        except Exception as e:
            logger.error(f"Erreur run_morning_briefs: {e}")

        await asyncio.sleep(60)  # Vérifie toutes les minutes

# ─── Job : alertes de prix ───────────────────────────────────────

async def run_price_alerts(bot: Bot):
    """Tourne toutes les 5 minutes, vérifie les alertes actives."""
    while True:
        try:
            alerts = await get_all_active_alerts()
            if not alerts:
                await asyncio.sleep(300)
                continue

            market = await fetch_market_data()
            if not market:
                await asyncio.sleep(300)
                continue

            prices = {
                "BTC": market["btc_price"],
                "ETH": market["eth_price"],
                "SOL": market["sol_price"],
            }

            for alert in alerts:
                symbol = alert["symbol"].upper().replace("/USDT", "").replace("/USD", "")
                current_price = prices.get(symbol)
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
                    messages = {
                        "fr": (
                            f"🔔 *Alerte déclenchée !*\n\n"
                            f"{symbol} a atteint ${current_price:,.0f}\n"
                            f"Ton objectif était : {direction} ${target:,.0f}\n\n"
                            f"💡 Analyse la situation avant d'agir."
                        ),
                        "en": (
                            f"🔔 *Alert triggered!*\n\n"
                            f"{symbol} reached ${current_price:,.0f}\n"
                            f"Your target was: {direction} ${target:,.0f}\n\n"
                            f"💡 Analyze the situation before acting."
                        ),
                        "es": (
                            f"🔔 *¡Alerta activada!*\n\n"
                            f"{symbol} ha alcanzado ${current_price:,.0f}\n"
                            f"Tu objetivo era: {direction} ${target:,.0f}\n\n"
                            f"💡 Analiza la situación antes de actuar."
                        ),
                        "pt": (
                            f"🔔 *Alerta disparado!*\n\n"
                            f"{symbol} atingiu ${current_price:,.0f}\n"
                            f"Seu alvo era: {direction} ${target:,.0f}\n\n"
                            f"💡 Analise a situação antes de agir."
                        ),
                    }
                    try:
                        await bot.send_message(
                            alert["user_id"],
                            messages.get(lang, messages["fr"]),
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logger.error(f"Erreur alerte {alert['id']}: {e}")

        except Exception as e:
            logger.error(f"Erreur run_price_alerts: {e}")

        await asyncio.sleep(300)  # Vérifie toutes les 5 minutes
