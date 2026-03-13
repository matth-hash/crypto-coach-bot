import asyncio
import ccxt.async_support as ccxt_async
from datetime import datetime, timezone

# ─── Récupération OHLCV ──────────────────────────────────────────

TIMEFRAME_MAP = {"H1": "1h", "H4": "4h", "D1": "1d"}
CANDLES_NEEDED = 100

# ─── Indicateurs techniques ──────────────────────────────────────

def compute_rsi(closes: list, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = closes[-period + i - 1] - closes[-period + i - 2] if i > 1 else closes[-period] - closes[-period - 1]
        (gains if diff > 0 else losses).append(abs(diff))

    deltas = [closes[i] - closes[i - 1] for i in range(len(closes) - period, len(closes))]
    gains = [d for d in deltas if d > 0]
    losses = [abs(d) for d in deltas if d < 0]

    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0.001

    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)

def compute_macd(closes: list) -> dict:
    """Retourne MACD line, signal line et histogram."""
    def ema(data, period):
        k = 2 / (period + 1)
        result = [data[0]]
        for price in data[1:]:
            result.append(price * k + result[-1] * (1 - k))
        return result

    if len(closes) < 35:
        return {"macd": 0, "signal": 0, "histogram": 0, "cross": "neutral"}

    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    macd_line = [ema12[i] - ema26[i] for i in range(len(closes))]
    signal_line = ema(macd_line, 9)
    histogram = macd_line[-1] - signal_line[-1]
    prev_histogram = macd_line[-2] - signal_line[-2]

    if histogram > 0 and prev_histogram <= 0:
        cross = "bullish"
    elif histogram < 0 and prev_histogram >= 0:
        cross = "bearish"
    else:
        cross = "neutral"

    return {
        "macd": round(macd_line[-1], 4),
        "signal": round(signal_line[-1], 4),
        "histogram": round(histogram, 4),
        "cross": cross,
    }

def compute_fibonacci(highs: list, lows: list) -> dict:
    """Calcule les niveaux de retracement Fibonacci sur les 50 dernières bougies."""
    recent_high = max(highs[-50:])
    recent_low = min(lows[-50:])
    diff = recent_high - recent_low
    return {
        "high": round(recent_high, 2),
        "low": round(recent_low, 2),
        "0.382": round(recent_high - diff * 0.382, 2),
        "0.500": round(recent_high - diff * 0.500, 2),
        "0.618": round(recent_high - diff * 0.618, 2),
    }

def average_volume(volumes: list, period: int = 20) -> float:
    if len(volumes) < period:
        return sum(volumes) / len(volumes)
    return sum(volumes[-period:]) / period

# ─── Détection de patterns ───────────────────────────────────────

def detect_head_and_shoulders(highs: list, lows: list, closes: list) -> dict | None:
    """Détecte Head & Shoulders et Inverse H&S."""
    if len(highs) < 30:
        return None

    h = highs[-30:]
    l = lows[-30:]

    # Cherche 3 pics pour H&S normal
    peaks = []
    for i in range(2, len(h) - 2):
        if h[i] > h[i-1] and h[i] > h[i-2] and h[i] > h[i+1] and h[i] > h[i+2]:
            peaks.append((i, h[i]))

    if len(peaks) >= 3:
        p1, p2, p3 = peaks[-3], peaks[-2], peaks[-1]
        # H&S : épaule gauche < tête > épaule droite, épaules ≈ même niveau
        if p2[1] > p1[1] and p2[1] > p3[1]:
            shoulder_diff = abs(p1[1] - p3[1]) / p2[1]
            if shoulder_diff < 0.05:  # épaules à moins de 5% d'écart
                neckline = (l[p1[0]] + l[p3[0]]) / 2
                target = neckline - (p2[1] - neckline)
                return {
                    "name": "Head & Shoulders",
                    "type": "bearish",
                    "neckline": round(neckline, 2),
                    "target": round(target, 2),
                    "alert_condition": "below",
                    "alert_price": round(neckline, 2),
                }

    # Cherche 3 creux pour Inverse H&S
    troughs = []
    for i in range(2, len(l) - 2):
        if l[i] < l[i-1] and l[i] < l[i-2] and l[i] < l[i+1] and l[i] < l[i+2]:
            troughs.append((i, l[i]))

    if len(troughs) >= 3:
        t1, t2, t3 = troughs[-3], troughs[-2], troughs[-1]
        if t2[1] < t1[1] and t2[1] < t3[1]:
            shoulder_diff = abs(t1[1] - t3[1]) / abs(t2[1])
            if shoulder_diff < 0.05:
                neckline = (h[t1[0]] + h[t3[0]]) / 2
                target = neckline + (neckline - t2[1])
                return {
                    "name": "Inverse Head & Shoulders",
                    "type": "bullish",
                    "neckline": round(neckline, 2),
                    "target": round(target, 2),
                    "alert_condition": "above",
                    "alert_price": round(neckline, 2),
                }
    return None

def detect_double_top_bottom(highs: list, lows: list) -> dict | None:
    """Détecte Double Top et Double Bottom."""
    if len(highs) < 20:
        return None

    h = highs[-30:]
    l = lows[-30:]

    # Double Top : deux pics proches
    peaks = [(i, h[i]) for i in range(2, len(h) - 2) if h[i] > h[i-1] and h[i] > h[i+1]]
    if len(peaks) >= 2:
        p1, p2 = peaks[-2], peaks[-1]
        if abs(p1[1] - p2[1]) / p1[1] < 0.03:  # moins de 3% d'écart
            neckline = min(l[p1[0]:p2[0]+1]) if p1[0] < p2[0] else min(l)
            target = neckline - (p1[1] - neckline)
            return {
                "name": "Double Top",
                "type": "bearish",
                "neckline": round(neckline, 2),
                "target": round(target, 2),
                "alert_condition": "below",
                "alert_price": round(neckline, 2),
            }

    # Double Bottom : deux creux proches
    troughs = [(i, l[i]) for i in range(2, len(l) - 2) if l[i] < l[i-1] and l[i] < l[i+1]]
    if len(troughs) >= 2:
        t1, t2 = troughs[-2], troughs[-1]
        if abs(t1[1] - t2[1]) / t1[1] < 0.03:
            neckline = max(h[t1[0]:t2[0]+1]) if t1[0] < t2[0] else max(h)
            target = neckline + (neckline - t1[1])
            return {
                "name": "Double Bottom",
                "type": "bullish",
                "neckline": round(neckline, 2),
                "target": round(target, 2),
                "alert_condition": "above",
                "alert_price": round(neckline, 2),
            }
    return None

def detect_triangle(highs: list, lows: list, closes: list) -> dict | None:
    """Détecte Triangle ascendant, descendant ou symétrique."""
    if len(highs) < 20:
        return None

    h = highs[-20:]
    l = lows[-20:]

    high_slope = h[-1] - h[0]
    low_slope = l[-1] - l[0]
    current = closes[-1]

    # Triangle ascendant : résistance plate, support montant
    if abs(high_slope) / h[0] < 0.02 and low_slope > 0:
        resistance = max(h)
        return {
            "name": "Triangle Ascendant",
            "type": "bullish",
            "neckline": round(resistance, 2),
            "target": round(resistance * 1.05, 2),
            "alert_condition": "above",
            "alert_price": round(resistance, 2),
        }

    # Triangle descendant : support plat, résistance descendante
    if abs(low_slope) / l[0] < 0.02 and high_slope < 0:
        support = min(l)
        return {
            "name": "Triangle Descendant",
            "type": "bearish",
            "neckline": round(support, 2),
            "target": round(support * 0.95, 2),
            "alert_condition": "below",
            "alert_price": round(support, 2),
        }

    # Triangle symétrique : convergence
    if high_slope < 0 and low_slope > 0:
        apex = (h[-1] + l[-1]) / 2
        return {
            "name": "Triangle Symétrique",
            "type": "neutral",
            "neckline": round(apex, 2),
            "target": None,
            "alert_condition": "above",
            "alert_price": round(max(h[-5:]), 2),
        }
    return None

def detect_flag(highs: list, lows: list, closes: list, volumes: list) -> dict | None:
    """Détecte Bull Flag et Bear Flag."""
    if len(closes) < 20:
        return None

    # Mouvement fort sur les 10 premières bougies puis consolidation
    move = closes[-10] - closes[-20]
    consolidation = closes[-1] - closes[-10]
    avg_vol = average_volume(volumes, 20)
    recent_vol = volumes[-1]

    # Bull Flag : forte hausse puis légère baisse / consolidation
    if move > 0 and move / closes[-20] > 0.05 and abs(consolidation) < move * 0.5:
        if consolidation <= 0:
            return {
                "name": "Bull Flag",
                "type": "bullish",
                "neckline": round(max(highs[-5:]), 2),
                "target": round(closes[-1] + move, 2),
                "alert_condition": "above",
                "alert_price": round(max(highs[-5:]), 2),
            }

    # Bear Flag : forte baisse puis légère hausse / consolidation
    if move < 0 and abs(move) / closes[-20] > 0.05 and abs(consolidation) < abs(move) * 0.5:
        if consolidation >= 0:
            return {
                "name": "Bear Flag",
                "type": "bearish",
                "neckline": round(min(lows[-5:]), 2),
                "target": round(closes[-1] + move, 2),
                "alert_condition": "below",
                "alert_price": round(min(lows[-5:]), 2),
            }
    return None

def detect_support_resistance(highs: list, lows: list, closes: list) -> dict:
    """Identifie support et résistance clés."""
    support = round(min(lows[-20:]), 2)
    resistance = round(max(highs[-20:]), 2)
    current = closes[-1]

    # Distance par rapport aux niveaux
    dist_sup = abs(current - support) / current
    dist_res = abs(resistance - current) / current

    closest = "support" if dist_sup < dist_res else "resistance"
    alert_price = support if closest == "support" else resistance
    alert_condition = "below" if closest == "support" else "above"

    return {
        "name": "Support & Résistance",
        "type": "neutral",
        "support": support,
        "resistance": resistance,
        "closest": closest,
        "alert_condition": alert_condition,
        "alert_price": alert_price,
        "neckline": alert_price,
        "target": None,
    }

# ─── Scoring fiabilité ───────────────────────────────────────────

def compute_reliability_score(pattern: dict, rsi: float, macd: dict, volumes: list, multitf: bool) -> int:
    """Score de 1 à 5 étoiles."""
    score = 1

    pattern_type = pattern.get("type", "neutral")

    # RSI aligné avec le pattern
    if pattern_type == "bullish" and rsi < 50:
        score += 1
    elif pattern_type == "bearish" and rsi > 50:
        score += 1
    elif pattern_type == "neutral":
        score += 1

    # MACD aligné
    if pattern_type == "bullish" and macd["cross"] == "bullish":
        score += 1
    elif pattern_type == "bearish" and macd["cross"] == "bearish":
        score += 1
    elif pattern_type == "neutral":
        score += 0

    # Volume supérieur à la moyenne
    avg_vol = average_volume(volumes, 20)
    if volumes[-1] > avg_vol * 1.2:
        score += 1

    # Confirmation multi-timeframe
    if multitf:
        score += 1

    return min(score, 5)

# ─── Analyse complète ────────────────────────────────────────────

async def fetch_ohlcv_raw(exchange, symbol: str, timeframe: str) -> list:
    """Fetch OHLCV en réutilisant une instance exchange existante."""
    try:
        tf = TIMEFRAME_MAP.get(timeframe, "4h")
        pair = f"{symbol}/USDT"
        return await exchange.fetch_ohlcv(pair, tf, limit=CANDLES_NEEDED)
    except Exception as e:
        print(f"Erreur OHLCV {symbol}/{timeframe}: {e}")
        return []

async def analyze_asset(symbol: str, timeframe: str, check_multitf: bool = True) -> dict | None:
    """Analyse complète d'un asset : patterns + indicateurs + score."""
    try:
        async with ccxt_async.binance({"enableRateLimit": True}) as exchange:
            ohlcv = await fetch_ohlcv_raw(exchange, symbol, timeframe)
            if len(ohlcv) < 30:
                return None

            highs  = [c[2] for c in ohlcv]
            lows   = [c[3] for c in ohlcv]
            closes = [c[4] for c in ohlcv]
            vols   = [c[5] for c in ohlcv]

            rsi  = compute_rsi(closes)
            macd = compute_macd(closes)
            fib  = compute_fibonacci(highs, lows)
            avg_vol = average_volume(vols)
            vol_ratio = round(vols[-1] / avg_vol, 2) if avg_vol > 0 else 1.0

            pattern = (
                detect_head_and_shoulders(highs, lows, closes) or
                detect_double_top_bottom(highs, lows) or
                detect_triangle(highs, lows, closes) or
                detect_flag(highs, lows, closes, vols) or
                detect_support_resistance(highs, lows, closes)
            )

            # Vérification multi-timeframe — même instance exchange
            multitf = False
            if check_multitf and timeframe in ("H1", "H4"):
                upper_tf = "D1" if timeframe == "H4" else "H4"
                ohlcv_upper = await fetch_ohlcv_raw(exchange, symbol, upper_tf)
                if len(ohlcv_upper) >= 30:
                    h2 = [c[2] for c in ohlcv_upper]
                    l2 = [c[3] for c in ohlcv_upper]
                    c2 = [c[4] for c in ohlcv_upper]
                    upper_pattern = (
                        detect_head_and_shoulders(h2, l2, c2) or
                        detect_double_top_bottom(h2, l2) or
                        detect_triangle(h2, l2, c2)
                    )
                    if upper_pattern and upper_pattern.get("type") == pattern.get("type"):
                        multitf = True

            stars = compute_reliability_score(pattern, rsi, macd, vols, multitf)

            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "pattern": pattern,
                "rsi": rsi,
                "macd": macd,
                "fib": fib,
                "vol_ratio": vol_ratio,
                "multitf": multitf,
                "stars": stars,
                "current_price": closes[-1],
            }
    except Exception as e:
        print(f"Erreur analyze_asset {symbol}/{timeframe}: {e}")
        return None
