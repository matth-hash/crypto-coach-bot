import asyncpg
import os
import json
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")

# Pool de connexions global
pool = None

async def init_db():
    """Initialise la connexion et crée les tables si elles n'existent pas."""
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)

    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                language TEXT DEFAULT 'en',
                level TEXT,
                trading_style TEXT,
                goal TEXT,
                xp INTEGER DEFAULT 0,
                streak_days INTEGER DEFAULT 0,
                last_active TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS psychological_profile (
                user_id BIGINT PRIMARY KEY REFERENCES users(user_id),
                fomo_score INTEGER DEFAULT 50,
                patience_score INTEGER DEFAULT 50,
                risk_discipline INTEGER DEFAULT 50,
                detected_biases TEXT DEFAULT '[]',
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)

    print("✅ Base de données initialisée !")

# ─── Fonctions utilisateur ───────────────────────────────────────

async def get_user(user_id: int) -> dict | None:
    """Récupère le profil complet d'un utilisateur."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE user_id = $1", user_id
        )
        if row:
            return dict(row)
        return None

async def create_user(user_id: int, username: str, language: str) -> dict:
    """Crée un nouvel utilisateur."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO users (user_id, username, language)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO UPDATE
            SET username = $2, last_active = NOW()
            RETURNING *
        """, user_id, username, language)

        # Créer son profil psychologique vide
        await conn.execute("""
            INSERT INTO psychological_profile (user_id)
            VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING
        """, user_id)

        return dict(row)

async def update_user_profile(user_id: int, **kwargs) -> None:
    """Met à jour n'importe quel champ du profil utilisateur."""
    if not kwargs:
        return

    fields = ", ".join(
        f"{key} = ${i+2}" for i, key in enumerate(kwargs.keys())
    )
    values = list(kwargs.values())

    async with pool.acquire() as conn:
        await conn.execute(
            f"UPDATE users SET {fields}, last_active = NOW() WHERE user_id = $1",
            user_id, *values
        )

async def update_xp(user_id: int, points: int = 10) -> int:
    """Ajoute des XP à l'utilisateur et retourne le nouveau total."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            UPDATE users SET xp = xp + $2, last_active = NOW()
            WHERE user_id = $1
            RETURNING xp
        """, user_id, points)
        return row["xp"]

# ─── Fonctions conversation ──────────────────────────────────────

async def save_message(user_id: int, role: str, content: str) -> None:
    """Sauvegarde un message dans l'historique."""
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO conversations (user_id, role, content)
            VALUES ($1, $2, $3)
        """, user_id, role, content)

async def get_conversation_history(user_id: int, limit: int = 20) -> list:
    """Récupère les derniers messages pour le contexte IA."""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT role, content FROM conversations
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """, user_id, limit)

        # Inverser pour avoir l'ordre chronologique
        messages = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
        return messages

async def clear_conversation_history(user_id: int) -> None:
    """Efface l'historique de conversation."""
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM conversations WHERE user_id = $1", user_id
        )

# ─── Fonctions profil psychologique ─────────────────────────────

async def get_psychological_profile(user_id: int) -> dict | None:
    """Récupère le profil psychologique."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM psychological_profile WHERE user_id = $1", user_id
        )
        if row:
            data = dict(row)
            data["detected_biases"] = json.loads(data["detected_biases"])
            return data
        return None

async def add_bias(user_id: int, bias: str) -> None:
    """Ajoute un biais détecté au profil psychologique."""
    profile = await get_psychological_profile(user_id)
    if not profile:
        return

    biases = profile["detected_biases"]
    if bias not in biases:
        biases.append(bias)

    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE psychological_profile
            SET detected_biases = $2, updated_at = NOW()
            WHERE user_id = $1
        """, user_id, json.dumps(biases))