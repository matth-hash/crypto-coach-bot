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

# Top 50 crypto pour le journal (CoinGecko IDs)
TOP_50_CRYPTOS = {
    "bitcoin": "BTC", "ethereum": "ETH", "tether": "USDT",
    "binancecoin": "BNB", "solana": "SOL", "ripple": "XRP",
    "usd-coin": "USDC", "staked-ether": "STETH", "cardano": "ADA",
    "avalanche-2": "AVAX", "dogecoin": "DOGE", "tron": "TRX",
    "polkadot": "DOT", "chainlink": "LINK", "polygon": "MATIC",
    "wrapped-bitcoin": "WBTC", "shiba-inu": "SHIB", "dai": "DAI",
    "litecoin": "LTC", "uniswap": "UNI", "bitcoin-cash": "BCH",
    "internet-computer": "ICP", "cosmos": "ATOM", "stellar": "XLM",
    "ethereum-classic": "ETC", "filecoin": "FIL", "aptos": "APT",
    "hedera-hashgraph": "HBAR", "near": "NEAR", "arbitrum": "ARB",
    "vechain": "VET", "the-graph": "GRT", "aave": "AAVE",
    "algorand": "ALGO", "quant-network": "QNT", "fantom": "FTM",
    "elrond-erd-2": "EGLD", "flow": "FLOW", "decentraland": "MANA",
    "sandbox": "SAND", "axie-infinity": "AXS", "theta-token": "THETA",
    "tezos": "XTZ", "eos": "EOS", "maker": "MKR",
    "injective-protocol": "INJ", "sui": "SUI", "pepe": "PEPE",
    "optimism": "OP", "render-token": "RNDR",
}

# Actions US
STOCKS = {
    "AAPL": "Apple", "TSLA": "Tesla", "NVDA": "Nvidia",
    "MSFT": "Microsoft", "AMZN": "Amazon", "GOOGL": "Google",
    "META": "Meta", "NFLX": "Netflix", "AMD": "AMD",
    "COIN": "Coinbase",
}

# Indices et matières premières
INDICES = {
    "^GSPC": "SP500", "^IXIC": "NASDAQ", "^FCHI": "CAC40",
    "^GDAXI": "DAX", "GC=F": "Gold", "SI=F": "Silver", "CL=F": "Oil",
}

async def get_metals_prices() -> dict:
    """Récupère les prix de l'or et l'argent via Yahoo Finance."""
    try:
        import yfinance as yf

        def fetch():
            metals = {}
            gold = yf.Ticker("GC=F")
            silver = yf.Ticker("SI=F")
            gold_info = gold.fast_info
            silver_info = silver.fast_info
            if gold_info.last_price:
                metals["XAU"] = {"price": round(gold_info.last_price, 2), "change_24h": 0}
            if silver_info.last_price:
                metals["XAG"] = {"price": round(silver_info.last_price, 2), "change_24h": 0}
            return metals

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, fetch)
    except Exception as e:
        print(f"Erreur metals yfinance: {e}")
        return {}

# Cache simple
_cache = {}
_cache_time = None
_cache_top50 = {}
_cache_top50_time = None
CACHE_DURATION = 300  # 5 minutes

async def get_crypto_prices() -> dict:
    """Récupère les prix en temps réel via CoinGecko (top 10)."""
    global _cache, _cache_time
    now = datetime.now(timezone.utc).timestamp()
    if _cache and _cache_time and (now - _cache_time) < CACHE_DURATION:
        return _cache
    try:
        ids = ",".join(TOP_CRYPTOS.keys())
        url = (
            f"https://api.coingecko.com/api/v3/simple/price"
            f"?ids={ids}&vs_currencies=usd"
            f"&include_24hr_change=true&include_market_cap=true"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
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

async def get_top50_prices() -> dict:
    """Récupère les prix du top 50 crypto pour le journal."""
    global _cache_top50, _cache_top50_time
    now = datetime.now(timezone.utc).timestamp()
    if _cache_top50 and _cache_top50_time and (now - _cache_top50_time) < CACHE_DURATION:
        return _cache_top50
    try:
        ids = ",".join(TOP_50_CRYPTOS.keys())
        url = (
            f"https://api.coingecko.com/api/v3/simple/price"
            f"?ids={ids}&vs_currencies=usd&include_24hr_change=true"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    prices = {}
                    for coin_id, symbol in TOP_50_CRYPTOS.items():
                        if coin_id in data:
                            prices[symbol] = {
                                "price": data[coin_id].get("usd", 0),
                                "change_24h": data[coin_id].get("usd_24h_change", 0),
                            }
                    _cache_top50 = prices
                    _cache_top50_time = now
                    return prices
    except Exception as e:
        print(f"Erreur CoinGecko top50: {e}")
    return _cache_top50 if _cache_top50 else {}

async def get_stock_prices(symbols: list) -> dict:
    """Récupère les prix d'actions/indices via yfinance."""
    try:
        import yfinance as yf

        def fetch():
            result = {}
            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.fast_info
                    if info.last_price:
                        result[symbol] = {"price": round(info.last_price, 2), "change_24h": 0}
                except Exception:
                    continue
            return result

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, fetch)
    except Exception as e:
        print(f"Erreur yfinance stocks: {e}")
        return {}

async def get_fear_greed_index() -> dict:
    """Récupère le Fear & Greed Index via alternative.me."""
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

async def get_btc_dominance() -> float:
    """Récupère la dominance BTC via CoinGecko global."""
    try:
        url = "https://api.coingecko.com/api/v3/global"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", {}).get("market_cap_percentage", {}).get("btc", 50.0)
    except Exception as e:
        print(f"Erreur BTC dominance: {e}")
    return 50.0

async def get_market_score() -> dict:
    """
    Calcule un score de marché de 0 à 100.
    Pondération : Fear&Greed 40%, BTC change 30%, ETH change 15%, BTC dominance 15%
    """
    try:
        prices, fg, dominance = await asyncio.gather(
            get_crypto_prices(),
            get_fear_greed_index(),
            get_btc_dominance(),
        )

        fg_score = fg["value"]  # 0-100

        btc_change = prices.get("BTC", {}).get("change_24h", 0)
        eth_change = prices.get("ETH", {}).get("change_24h", 0)

        # Normalise les variations (-10% → 0, +10% → 100)
        btc_score = max(0, min(100, 50 + btc_change * 5))
        eth_score = max(0, min(100, 50 + eth_change * 5))

        # Dominance BTC : autour de 50% = neutre
        # > 55% = bear alt, < 45% = alt season (risque)
        # Score neutre à 50% dominance
        dom_score = max(0, min(100, 100 - abs(dominance - 50) * 2))

        score = int(
            fg_score * 0.40 +
            btc_score * 0.30 +
            eth_score * 0.15 +
            dom_score * 0.15
        )

        if score >= 70:
            label = {"fr": "🟢 Favorable", "en": "🟢 Favorable", "es": "🟢 Favorable", "pt": "🟢 Favorável"}
            emoji = "🟢"
        elif score >= 45:
            label = {"fr": "🟡 Neutre", "en": "🟡 Neutral", "es": "🟡 Neutral", "pt": "🟡 Neutro"}
            emoji = "🟡"
        else:
            label = {"fr": "🔴 Défavorable", "en": "🔴 Unfavorable", "es": "🔴 Desfavorable", "pt": "🔴 Desfavorável"}
            emoji = "🔴"

        return {
            "score": score,
            "label": label,
            "emoji": emoji,
            "fg": fg_score,
            "btc_change": btc_change,
            "eth_change": eth_change,
            "dominance": dominance,
        }
    except Exception as e:
        print(f"Erreur get_market_score: {e}")
        return {"score": 50, "label": {"fr": "🟡 Neutre", "en": "🟡 Neutral", "es": "🟡 Neutral", "pt": "🟡 Neutro"}, "emoji": "🟡"}

async def format_market_context(lang: str) -> str:
    """Formate le contexte de marché pour injection dans le prompt IA."""
    prices = await get_crypto_prices()
    metals = await get_metals_prices()
    fear_greed = await get_fear_greed_index()

    if not prices:
        return ""

    lines = []
    for symbol, data in prices.items():
        change = data["change_24h"]
        arrow = "📈" if change > 0 else "📉"
        lines.append(f"{arrow} {symbol}: ${data['price']:,.2f} ({change:+.1f}% 24h)")

    if metals:
        lines.append("─────────────────")
        metal_labels = {"XAU": "🥇 Or (Gold)", "XAG": "🥈 Argent (Silver)"}
        for symbol, data in metals.items():
            label = metal_labels.get(symbol, symbol)
            lines.append(f"{label}: ${data['price']:,.2f}/oz")

    fg_value = fear_greed["value"]
    fg_class = fear_greed["classification"]

    if fg_value <= 25:      fg_emoji = "😱"
    elif fg_value <= 45:    fg_emoji = "😰"
    elif fg_value <= 55:    fg_emoji = "😐"
    elif fg_value <= 75:    fg_emoji = "😊"
    else:                   fg_emoji = "🤑"

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
