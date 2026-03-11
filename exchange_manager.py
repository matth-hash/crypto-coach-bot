import ccxt.async_support as ccxt_async
from datetime import datetime, timezone

SUPPORTED_EXCHANGES = {
    "binance": "Binance",
    "bybit": "Bybit",
    "kucoin": "KuCoin",
    "okx": "OKX",
    "kraken": "Kraken",
}

async def test_connection(exchange_id: str, api_key: str, api_secret: str) -> dict:
    exchange = None
    try:
        exchange_class = getattr(ccxt_async, exchange_id)
        exchange = exchange_class({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        })

        # Utilise fetch_balance avec type 'spot' uniquement
        # → appelle /api/v3/account au lieu de /sapi/v1/capital/config/getall
        # → ne nécessite que la permission "Lecture seule"
        if exchange_id == "binance":
            balance = await exchange.fetch_balance({"type": "spot"})
        else:
            balance = await exchange.fetch_balance()

        total_assets = {k: v for k, v in balance["total"].items() if v > 0}
        return {
            "success": True,
            "message": "Connexion réussie",
            "assets_count": len(total_assets)
        }
    except ccxt_async.AuthenticationError:
        return {"success": False, "message": "Clés API invalides"}
    except ccxt_async.PermissionDenied:
        return {"success": False, "message": "Permissions insuffisantes — active 'Lecture seule' sur ta clé Binance"}
    except Exception as e:
        return {"success": False, "message": f"Erreur : {str(e)[:100]}"}
    finally:
        if exchange:
            await exchange.close()

async def fetch_recent_trades(
    exchange_id: str, api_key: str, api_secret: str, limit: int = 20
) -> list:
    exchange = None
    try:
        exchange_class = getattr(ccxt_async, exchange_id)
        exchange = exchange_class({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        })
        await exchange.load_markets()
        all_trades = []
        common_pairs = [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT",
            "XRP/USDT", "ADA/USDT", "DOGE/USDT", "MATIC/USDT",
            "BTC/USD", "ETH/USD",
            "BTC/USDC", "ETH/USDC"
        ]
        for pair in common_pairs:
            if pair not in exchange.markets:
                continue
            try:
                trades = await exchange.fetch_my_trades(pair, limit=5)
                all_trades.extend(trades)
            except Exception:
                continue

        all_trades.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_trades[:limit]
    except Exception as e:
        print(f"Erreur fetch trades: {e}")
        return []
    finally:
        if exchange:
            await exchange.close()

def format_trades_for_analysis(trades: list) -> str:
    if not trades:
        return "Aucun trade récent trouvé."
    formatted = []
    for t in trades[:10]:
        date = datetime.fromtimestamp(
            t["timestamp"] / 1000, tz=timezone.utc
        ).strftime("%d/%m/%Y %H:%M")
        side = "🟢 ACHAT" if t["side"] == "buy" else "🔴 VENTE"
        formatted.append(
            f"{side} {t['symbol']} | "
            f"Prix: {t['price']:.4f} | "
            f"Qté: {t['amount']:.4f} | "
            f"Date: {date}"
        )
    return "\n".join(formatted)
