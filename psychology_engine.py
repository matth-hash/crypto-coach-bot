from datetime import datetime, timezone, timedelta
from database import (
    get_psychological_profile, add_bias,
    get_recent_trades, get_user
)

# ─── Définition des biais ────────────────────────────────────────

BIASES = {
    "fomo": {
        "fr": "FOMO (peur de manquer)",
        "en": "FOMO (fear of missing out)",
        "es": "FOMO (miedo a perderse algo)",
        "pt": "FOMO (medo de perder)",
    },
    "revenge_trading": {
        "fr": "Revenge trading",
        "en": "Revenge trading",
        "es": "Revenge trading",
        "pt": "Revenge trading",
    },
    "early_profit_taking": {
        "fr": "Prise de profit prématurée",
        "en": "Early profit taking",
        "es": "Toma de ganancias prematura",
        "pt": "Realização de lucro prematuro",
    },
    "overtrading": {
        "fr": "Overtrading (trop de trades)",
        "en": "Overtrading",
        "es": "Overtrading",
        "pt": "Overtrading",
    },
    "loss_aversion": {
        "fr": "Aversion aux pertes",
        "en": "Loss aversion",
        "es": "Aversión a las pérdidas",
        "pt": "Aversão à perda",
    },
}

# ─── Alertes circuit breaker ─────────────────────────────────────

CIRCUIT_BREAKER_RULES = {
    "too_many_trades": {
        "threshold": 5,
        "window_hours": 2,
        "message": {
            "fr": (
                "⚠️ *Circuit Breaker activé*\n\n"
                "Tu as effectué {count} trades en moins de {hours}h.\n"
                "C'est un signe classique d'overtrading émotionnel.\n\n"
                "💡 *Conseil :* Prends une pause de 30 minutes. "
                "Les meilleurs trades se font avec un esprit calme."
            ),
            "en": (
                "⚠️ *Circuit Breaker Activated*\n\n"
                "You made {count} trades in less than {hours}h.\n"
                "This is a classic sign of emotional overtrading.\n\n"
                "💡 *Tip:* Take a 30-minute break. "
                "The best trades are made with a calm mind."
            ),
            "es": (
                "⚠️ *Circuit Breaker Activado*\n\n"
                "Hiciste {count} trades en menos de {hours}h.\n"
                "Es una señal clásica de overtrading emocional.\n\n"
                "💡 *Consejo:* Toma un descanso de 30 minutos."
            ),
            "pt": (
                "⚠️ *Circuit Breaker Ativado*\n\n"
                "Você fez {count} trades em menos de {hours}h.\n"
                "É um sinal clássico de overtrading emocional.\n\n"
                "💡 *Dica:* Faça uma pausa de 30 minutos."
            ),
        }
    },
    "high_drawdown": {
        "threshold_pct": -5.0,
        "message": {
            "fr": (
                "🔴 *Alerte Drawdown*\n\n"
                "Ton PnL est à {pnl:.1f}% aujourd'hui.\n"
                "Continuer à trader dans cet état augmente le risque "
                "de revenge trading.\n\n"
                "💡 *Conseil :* Fixe-toi une limite de perte journalière "
                "et respecte-la strictement."
            ),
            "en": (
                "🔴 *Drawdown Alert*\n\n"
                "Your PnL is at {pnl:.1f}% today.\n"
                "Continuing to trade in this state increases the risk "
                "of revenge trading.\n\n"
                "💡 *Tip:* Set a daily loss limit and stick to it."
            ),
            "es": (
                "🔴 *Alerta de Drawdown*\n\n"
                "Tu PnL está en {pnl:.1f}% hoy.\n"
                "Continuar tradingn en este estado aumenta el riesgo.\n\n"
                "💡 *Consejo:* Establece un límite de pérdida diaria."
            ),
            "pt": (
                "🔴 *Alerta de Drawdown*\n\n"
                "Seu PnL está em {pnl:.1f}% hoje.\n"
                "Continuar tradando neste estado aumenta o risco.\n\n"
                "💡 *Dica:* Defina um limite de perda diária."
            ),
        }
    },
    "night_trading": {
        "hours": [0, 1, 2, 3, 4],
        "message": {
            "fr": (
                "🌙 *Alerte Trading Nocturne*\n\n"
                "Il est tard et tu tradeas encore.\n"
                "La fatigue altère le jugement et augmente les erreurs.\n\n"
                "💡 *Conseil :* Va dormir. Les marchés seront là demain."
            ),
            "en": (
                "🌙 *Night Trading Alert*\n\n"
                "It's late and you're still trading.\n"
                "Fatigue impairs judgment and increases mistakes.\n\n"
                "💡 *Tip:* Go to sleep. Markets will be there tomorrow."
            ),
            "es": (
                "🌙 *Alerta de Trading Nocturno*\n\n"
                "Es tarde y sigues tradeando.\n"
                "La fatiga afecta el juicio.\n\n"
                "💡 *Consejo:* Ve a dormir. Los mercados estarán mañana."
            ),
            "pt": (
                "🌙 *Alerta de Trading Noturno*\n\n"
                "É tarde e você ainda está tradando.\n"
                "O cansaço prejudica o julgamento.\n\n"
                "💡 *Dica:* Vá dormir. Os mercados estarão lá amanhã."
            ),
        }
    }
}

# ─── Analyse des biais ───────────────────────────────────────────

async def analyze_trading_behavior(user_id: int, lang: str) -> list:
    """
    Analyse les trades récents et détecte les biais comportementaux.
    Retourne une liste d'alertes à envoyer à l'utilisateur.
    """
    alerts = []
    trades = await get_recent_trades(user_id, limit=20)

    if not trades:
        return alerts

    now = datetime.now(timezone.utc)

    # ── Détection overtrading ────────────────────────────────────
    window = timedelta(hours=2)
    recent_trades = [
        t for t in trades
        if t["created_at"] and (now - t["created_at"].replace(tzinfo=timezone.utc)) < window
    ]

    if len(recent_trades) >= CIRCUIT_BREAKER_RULES["too_many_trades"]["threshold"]:
        rule = CIRCUIT_BREAKER_RULES["too_many_trades"]
        msg = rule["message"].get(lang, rule["message"]["en"])
        alerts.append(msg.format(count=len(recent_trades), hours=2))
        await add_bias(user_id, "overtrading")

    # ── Détection drawdown ───────────────────────────────────────
    today_trades = [
        t for t in trades
        if t["created_at"] and (now - t["created_at"].replace(tzinfo=timezone.utc)).days == 0
        and t["pnl"] is not None
    ]

    if today_trades:
        total_pnl = sum(float(t["pnl"]) for t in today_trades)
        if total_pnl < CIRCUIT_BREAKER_RULES["high_drawdown"]["threshold_pct"]:
            rule = CIRCUIT_BREAKER_RULES["high_drawdown"]
            msg = rule["message"].get(lang, rule["message"]["en"])
            alerts.append(msg.format(pnl=total_pnl))
            await add_bias(user_id, "revenge_trading")

    # ── Détection trading nocturne ───────────────────────────────
    current_hour = now.hour
    if current_hour in CIRCUIT_BREAKER_RULES["night_trading"]["hours"]:
        if len(recent_trades) > 0:
            rule = CIRCUIT_BREAKER_RULES["night_trading"]
            alerts.append(rule["message"].get(lang, rule["message"]["en"]))

    return alerts

async def get_psychology_report(user_id: int, lang: str) -> str:
    """Génère un rapport psychologique complet."""
    profile = await get_psychological_profile(user_id)

    if not profile:
        no_data = {
            "fr": "Pas encore assez de données pour générer un rapport. Continue à trader !",
            "en": "Not enough data yet to generate a report. Keep trading!",
            "es": "Aún no hay suficientes datos. ¡Sigue tradingando!",
            "pt": "Ainda não há dados suficientes. Continue tradando!",
        }
        return no_data.get(lang, no_data["en"])

    biases = profile.get("detected_biases", [])

    if not biases:
        no_biases = {
            "fr": "✅ Aucun biais comportemental détecté pour le moment. Bon travail !",
            "en": "✅ No behavioral biases detected so far. Good job!",
            "es": "✅ No se detectaron sesgos conductuales. ¡Buen trabajo!",
            "pt": "✅ Nenhum viés comportamental detectado. Bom trabalho!",
        }
        return no_biases.get(lang, no_biases["en"])

    headers = {
        "fr": "🧠 *Rapport Psychologique*\n\n*Biais détectés :*\n",
        "en": "🧠 *Psychological Report*\n\n*Detected biases:*\n",
        "es": "🧠 *Informe Psicológico*\n\n*Sesgos detectados:*\n",
        "pt": "🧠 *Relatório Psicológico*\n\n*Vieses detectados:*\n",
    }

    report = headers.get(lang, headers["en"])

    for bias in biases:
        if bias in BIASES:
            report += f"• {BIASES[bias].get(lang, BIASES[bias]['en'])}\n"

    tips = {
        "fr": (
            "\n💡 *Comment progresser :*\n"
            "Discute de ces biais avec moi pour comprendre "
            "comment les corriger dans ta pratique quotidienne."
        ),
        "en": (
            "\n💡 *How to improve:*\n"
            "Discuss these biases with me to understand "
            "how to correct them in your daily practice."
        ),
        "es": (
            "\n💡 *Cómo mejorar:*\n"
            "Habla conmigo sobre estos sesgos para entender "
            "cómo corregirlos en tu práctica diaria."
        ),
        "pt": (
            "\n💡 *Como melhorar:*\n"
            "Discuta esses vieses comigo para entender "
            "como corrigi-los na sua prática diária."
        ),
    }

    report += tips.get(lang, tips["en"])
    return report