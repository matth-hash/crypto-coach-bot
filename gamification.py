from datetime import datetime, timezone, timedelta
from database import get_user, update_user_profile

# ─── Définition des niveaux ──────────────────────────────────────

LEVELS = [
    {"min_xp": 0,    "level": 1, "name": {"fr": "🌱 Débutant",        "en": "🌱 Beginner",      "es": "🌱 Principiante",  "pt": "🌱 Iniciante"}},
    {"min_xp": 100,  "level": 2, "name": {"fr": "📈 Apprenti",         "en": "📈 Apprentice",    "es": "📈 Aprendiz",      "pt": "📈 Aprendiz"}},
    {"min_xp": 300,  "level": 3, "name": {"fr": "⚡ Trader Junior",    "en": "⚡ Junior Trader",  "es": "⚡ Trader Junior",  "pt": "⚡ Trader Júnior"}},
    {"min_xp": 600,  "level": 4, "name": {"fr": "🎯 Trader Confirmé",  "en": "🎯 Confirmed Trader","es": "🎯 Trader Confirmado","pt": "🎯 Trader Confirmado"}},
    {"min_xp": 1000, "level": 5, "name": {"fr": "🔥 Trader Avancé",   "en": "🔥 Advanced Trader","es": "🔥 Trader Avanzado", "pt": "🔥 Trader Avançado"}},
    {"min_xp": 2000, "level": 6, "name": {"fr": "💎 Expert",           "en": "💎 Expert",         "es": "💎 Experto",        "pt": "💎 Especialista"}},
    {"min_xp": 5000, "level": 7, "name": {"fr": "👑 Maître Trader",    "en": "👑 Master Trader",  "es": "👑 Maestro Trader", "pt": "👑 Mestre Trader"}},
]

# ─── Définition des badges ───────────────────────────────────────

BADGES = {
    "first_message": {
        "icon": "💬",
        "name": {"fr": "Premier pas",      "en": "First step",       "es": "Primer paso",     "pt": "Primeiro passo"},
        "desc": {"fr": "Premier message envoyé", "en": "First message sent", "es": "Primer mensaje enviado", "pt": "Primeira mensagem enviada"},
        "xp": 10,
    },
    "profile_complete": {
        "icon": "👤",
        "name": {"fr": "Profil complet",   "en": "Complete profile",  "es": "Perfil completo", "pt": "Perfil completo"},
        "desc": {"fr": "Profil configuré", "en": "Profile set up",    "es": "Perfil configurado", "pt": "Perfil configurado"},
        "xp": 20,
    },
    "exchange_connected": {
        "icon": "🔗",
        "name": {"fr": "Connecté",         "en": "Connected",         "es": "Conectado",       "pt": "Conectado"},
        "desc": {"fr": "Exchange connecté","en": "Exchange connected", "es": "Exchange conectado", "pt": "Exchange conectado"},
        "xp": 50,
    },
    "streak_3": {
        "icon": "🔥",
        "name": {"fr": "En feu !",         "en": "On fire!",          "es": "¡En llamas!",     "pt": "Em chamas!"},
        "desc": {"fr": "3 jours de suite", "en": "3 days in a row",   "es": "3 días seguidos", "pt": "3 dias seguidos"},
        "xp": 30,
    },
    "streak_7": {
        "icon": "⚡",
        "name": {"fr": "Semaine parfaite", "en": "Perfect week",      "es": "Semana perfecta", "pt": "Semana perfeita"},
        "desc": {"fr": "7 jours de suite", "en": "7 days in a row",   "es": "7 días seguidos", "pt": "7 dias seguidos"},
        "xp": 100,
    },
    "streak_30": {
        "icon": "👑",
        "name": {"fr": "Invaincu",         "en": "Undefeated",        "es": "Invicto",         "pt": "Invicto"},
        "desc": {"fr": "30 jours de suite","en": "30 days in a row",  "es": "30 días seguidos","pt": "30 dias seguidos"},
        "xp": 500,
    },
    "first_trade_analysis": {
        "icon": "📊",
        "name": {"fr": "Analyste",         "en": "Analyst",           "es": "Analista",        "pt": "Analista"},
        "desc": {"fr": "Premier trade analysé", "en": "First trade analyzed", "es": "Primer trade analizado", "pt": "Primeiro trade analisado"},
        "xp": 40,
    },
    "psycho_check": {
        "icon": "🧠",
        "name": {"fr": "Conscience de soi","en": "Self-aware",        "es": "Autoconsciente",  "pt": "Autoconsciente"},
        "desc": {"fr": "Premier rapport psycho", "en": "First psych report", "es": "Primer informe psico", "pt": "Primeiro relatório psico"},
        "xp": 30,
    },
    "no_bias_week": {
        "icon": "🎯",
        "name": {"fr": "Esprit clair",     "en": "Clear mind",        "es": "Mente clara",     "pt": "Mente clara"},
        "desc": {"fr": "Semaine sans biais","en": "Week without bias", "es": "Semana sin sesgos","pt": "Semana sem vieses"},
        "xp": 80,
    },
}

# ─── Fonctions utilitaires ───────────────────────────────────────

def get_level_info(xp: int, lang: str) -> dict:
    """Retourne les infos du niveau actuel et la progression vers le suivant."""
    current = LEVELS[0]
    next_level = None

    for i, lvl in enumerate(LEVELS):
        if xp >= lvl["min_xp"]:
            current = lvl
            if i + 1 < len(LEVELS):
                next_level = LEVELS[i + 1]

    progress = 0
    if next_level:
        range_xp = next_level["min_xp"] - current["min_xp"]
        earned_xp = xp - current["min_xp"]
        progress = int((earned_xp / range_xp) * 100)
    else:
        progress = 100

    return {
        "level": current["level"],
        "name": current["name"].get(lang, current["name"]["en"]),
        "next_level": next_level,
        "progress": progress,
        "xp_to_next": (next_level["min_xp"] - xp) if next_level else 0,
    }

def make_progress_bar(progress: int, length: int = 10) -> str:
    """Crée une barre de progression visuelle."""
    filled = int(length * progress / 100)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {progress}%"

async def check_and_award_badge(
    user_id: int, badge_key: str, lang: str
) -> str | None:
    """
    Vérifie si l'utilisateur mérite un badge et le lui attribue.
    Retourne le message de félicitations ou None si déjà obtenu.
    """
    from database import get_psychological_profile, update_xp
    import json

    profile = await get_psychological_profile(user_id)
    if not profile:
        return None

    # Vérifier si le badge est déjà obtenu (on stocke dans detected_biases
    # pour l'instant — on ajoutera une table dédiée plus tard)
    badge_key_stored = f"badge_{badge_key}"
    biases = profile.get("detected_biases", [])

    if badge_key_stored in biases:
        return None  # Badge déjà obtenu

    # Attribuer le badge
    from database import add_bias
    await add_bias(user_id, badge_key_stored)

    badge = BADGES.get(badge_key)
    if not badge:
        return None

    # Ajouter les XP du badge
    await update_xp(user_id, badge["xp"])

    congrats = {
        "fr": (
            f"🏆 *Nouveau badge débloqué !*\n\n"
            f"{badge['icon']} *{badge['name'].get(lang, badge['name']['en'])}*\n"
            f"{badge['desc'].get(lang, badge['desc']['en'])}\n\n"
            f"✨ +{badge['xp']} XP"
        ),
        "en": (
            f"🏆 *New badge unlocked!*\n\n"
            f"{badge['icon']} *{badge['name'].get(lang, badge['name']['en'])}*\n"
            f"{badge['desc'].get(lang, badge['desc']['en'])}\n\n"
            f"✨ +{badge['xp']} XP"
        ),
        "es": (
            f"🏆 *¡Nueva insignia desbloqueada!*\n\n"
            f"{badge['icon']} *{badge['name'].get(lang, badge['name']['en'])}*\n"
            f"{badge['desc'].get(lang, badge['desc']['en'])}\n\n"
            f"✨ +{badge['xp']} XP"
        ),
        "pt": (
            f"🏆 *Nova conquista desbloqueada!*\n\n"
            f"{badge['icon']} *{badge['name'].get(lang, badge['name']['en'])}*\n"
            f"{badge['desc'].get(lang, badge['desc']['en'])}\n\n"
            f"✨ +{badge['xp']} XP"
        ),
    }

    return congrats.get(lang, congrats["en"])

async def update_streak(user_id: int, lang: str) -> tuple[int, str | None]:
    """
    Met à jour le streak de l'utilisateur.
    Retourne (nouveau_streak, message_badge_ou_None)
    """
    from database import pool
    import asyncpg

    user = await get_user(user_id)
    if not user:
        return 0, None

    last_active = user.get("last_active")
    streak = user.get("streak_days", 0)
    now = datetime.now(timezone.utc)

    if last_active:
        last_active_utc = last_active.replace(tzinfo=timezone.utc)
        diff = now - last_active_utc

        if diff.days == 1:
            # Jour suivant → on incrémente
            streak += 1
        elif diff.days == 0:
            # Même jour → on ne change pas
            pass
        else:
            # Plus d'un jour → on remet à 1
            streak = 1
    else:
        streak = 1

    await update_user_profile(user_id, streak_days=streak)

    # Vérifier les badges de streak
    badge_msg = None
    if streak == 3:
        badge_msg = await check_and_award_badge(user_id, "streak_3", lang)
    elif streak == 7:
        badge_msg = await check_and_award_badge(user_id, "streak_7", lang)
    elif streak == 30:
        badge_msg = await check_and_award_badge(user_id, "streak_30", lang)

    return streak, badge_msg

async def get_badges_list(user_id: int, lang: str) -> list:
    """Retourne la liste des badges obtenus par l'utilisateur."""
    from database import get_psychological_profile

    profile = await get_psychological_profile(user_id)
    if not profile:
        return []

    biases = profile.get("detected_biases", [])
    obtained = []

    for key, badge in BADGES.items():
        if f"badge_{key}" in biases:
            obtained.append({
                "icon": badge["icon"],
                "name": badge["name"].get(lang, badge["name"]["en"]),
            })

    return obtained