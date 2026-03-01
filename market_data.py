import aiohttp
import asyncio
from datetime import datetime, timezone

# Top cryptos à suivre en permanence
TOP_CRYPTOS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "binancecoin": "BNB",
    "solana": "SOL",
    "ripple": "XRP",
    "cardano": "ADA",
    "dogecoin": "DOGE",
    "avalanche-2": "AVAX",
    "polkadot": "DOT",
    "chainlink": "LINK",
}

# Cache simple pour éviter trop d'appels API
_cache = {}
_cache_time = None
CACHE_DURATION = 300  # 5 minutes

async def get_crypto_prices() -> dict:
    """Récupère les prix en temps réel via CoinGecko."""
    global _cache, _cache_time

    now = datetime.now(timezone.utc).timestamp()

    # Retourner le cache si encore valide
    if _cache and _cache_time and (now - _cache_time) < CACHE_DURATION:
        return _cache

    try:
        ids = ",".join(TOP_CRYPTOS.keys())
        url = (
            f"https://api.coingecko.com/api/v3/simple/price"
            f"?ids={ids}&vs_currencies=usd"
            f"&include_24hr_change=true"
            f"&include_market_cap=true"
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()

                    # Formater les données
                    prices = {}
                    for coin_id, symbol in TOP_CRYPTOS.items():
                        if coin_id in data:
                            coin_data = data[coin_id]
                            prices[symbol] = {
                                "price": coin_data.get("usd", 0),
                                "change_24h": coin_data.get("usd_24h_change", 0),
                                "market_cap": coin_data.get("usd_market_cap", 0),
                            }

                    _cache = prices
                    _cache_time = now
                    return prices

    except Exception as e:
        print(f"Erreur CoinGecko: {e}")
        return _cache if _cache else {}

async def get_fear_greed_index() -> dict:
    """Récupère le Fear & Greed Index."""
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("data"):
                        item = data["data"][0]
                        return {
                            "value": int(item["value"]),
                            "classification": item["value_classification"],
                        }
    except Exception as e:
        print(f"Erreur Fear & Greed: {e}")

    return {"value": 50, "classification": "Neutral"}

async def format_market_context(lang: str) -> str:
    """Formate le contexte de marché pour injection dans le prompt IA."""
    prices = await get_crypto_prices()
    fear_greed = await get_fear_greed_index()

    if not prices:
        return ""

    # Construire le résumé de marché
    lines = []
    for symbol, data in prices.items():
        change = data["change_24h"]
        arrow = "📈" if change > 0 else "📉"
        lines.append(
            f"{arrow} {symbol}: ${data['price']:,.2f} "
            f"({change:+.1f}% 24h)"
        )

    fg_value = fear_greed["value"]
    fg_class = fear_greed["classification"]

    if fg_value <= 25:
        fg_emoji = "😱"
    elif fg_value <= 45:
        fg_emoji = "😰"
    elif fg_value <= 55:
        fg_emoji = "😐"
    elif fg_value <= 75:
        fg_emoji = "😊"
    else:
        fg_emoji = "🤑"

    market_headers = {
        "fr": "📊 DONNÉES DE MARCHÉ EN TEMPS RÉEL",
        "en": "📊 REAL-TIME MARKET DATA",
        "es": "📊 DATOS DE MERCADO EN TIEMPO REAL",
        "pt": "📊 DADOS DE MERCADO EM TEMPO REAL",
    }

    fg_labels = {
        "fr": f"😱 Fear & Greed Index : {fg_value}/100 ({fg_class}) {fg_emoji}",
        "en": f"😱 Fear & Greed Index: {fg_value}/100 ({fg_class}) {fg_emoji}",
        "es": f"😱 Fear & Greed Index: {fg_value}/100 ({fg_class}) {fg_emoji}",
        "pt": f"😱 Fear & Greed Index: {fg_value}/100 ({fg_class}) {fg_emoji}",
    }

    updated_labels = {
        "fr": f"🕐 Mis à jour : {datetime.now(timezone.utc).strftime('%H:%M UTC')}",
        "en": f"🕐 Updated: {datetime.now(timezone.utc).strftime('%H:%M UTC')}",
        "es": f"🕐 Actualizado: {datetime.now(timezone.utc).strftime('%H:%M UTC')}",
        "pt": f"🕐 Atualizado: {datetime.now(timezone.utc).strftime('%H:%M UTC')}",
    }

    context = (
        f"{market_headers.get(lang, market_headers['en'])}\n"
        + "\n".join(lines)
        + f"\n{fg_labels.get(lang, fg_labels['en'])}\n"
        + updated_labels.get(lang, updated_labels["en"])
    )

    return context