import asyncpg
import os
import json
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")

pool = None

async def init_db():
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
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS morning_time TEXT DEFAULT NULL
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

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS exchange_connections (
                user_id BIGINT REFERENCES users(user_id),
                exchange TEXT NOT NULL,
                api_key TEXT NOT NULL,
                api_secret TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (user_id, exchange)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                exchange TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                amount DECIMAL,
                price DECIMAL,
                pnl DECIMAL,
                trade_date TIMESTAMP,
                analysis TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id BIGINT PRIMARY KEY REFERENCES users(user_id),
                plan TEXT DEFAULT 'free',
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                status TEXT DEFAULT 'active',
                current_period_end TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                symbol TEXT NOT NULL,
                condition TEXT NOT NULL,
                target_price DECIMAL NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                triggered_at TIMESTAMP DEFAULT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS journal_trades (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price DECIMAL NOT NULL,
                exit_price DECIMAL DEFAULT NULL,
                amount DECIMAL NOT NULL,
                emotion TEXT NOT NULL,
                reason TEXT NOT NULL,
                pnl DECIMAL DEFAULT NULL,
                pnl_pct DECIMAL DEFAULT NULL,
                postmortem TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS detected_patterns (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                stars INTEGER DEFAULT 1,
                neckline DECIMAL DEFAULT NULL,
                target DECIMAL DEFAULT NULL,
                confirmed BOOLEAN DEFAULT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

    print("✅ Base de données initialisée !")

# ─── Fonctions utilisateur ───────────────────────────────────────

async def get_user(user_id: int) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE user_id = $1", user_id
        )
        if row:
            return dict(row)
        return None

async def create_user(user_id: int, username: str, language: str) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO users (user_id, username, language)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO UPDATE
            SET username = $2, last_active = NOW()
            RETURNING *
        """, user_id, username, language)

        await conn.execute("""
            INSERT INTO psychological_profile (user_id)
            VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING
        """, user_id)

        return dict(row)

async def update_user_profile(user_id: int, **kwargs) -> None:
    if not kwargs:
        return
    fields = ", ".join(f"{key} = ${i+2}" for i, key in enumerate(kwargs.keys()))
    values = list(kwargs.values())
    async with pool.acquire() as conn:
        await conn.execute(
            f"UPDATE users SET {fields}, last_active = NOW() WHERE user_id = $1",
            user_id, *values
        )

async def update_xp(user_id: int, points: int = 10) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            UPDATE users SET xp = xp + $2, last_active = NOW()
            WHERE user_id = $1
            RETURNING xp
        """, user_id, points)
        return row["xp"]

# ─── Fonctions conversation ──────────────────────────────────────

async def save_message(user_id: int, role: str, content: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO conversations (user_id, role, content)
            VALUES ($1, $2, $3)
        """, user_id, role, content)

async def get_conversation_history(user_id: int, limit: int = 20) -> list:
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT role, content FROM conversations
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """, user_id, limit)
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

async def clear_conversation_history(user_id: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM conversations WHERE user_id = $1", user_id)

# ─── Fonctions profil psychologique ─────────────────────────────

async def get_psychological_profile(user_id: int) -> dict | None:
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

# ─── Fonctions exchange ──────────────────────────────────────────

async def save_exchange_connection(user_id: int, exchange: str, api_key: str, api_secret: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO exchange_connections (user_id, exchange, api_key, api_secret)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, exchange) DO UPDATE
            SET api_key = $3, api_secret = $4
        """, user_id, exchange, api_key, api_secret)

async def get_exchange_connection(user_id: int, exchange: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM exchange_connections
            WHERE user_id = $1 AND exchange = $2
        """, user_id, exchange)
        return dict(row) if row else None

async def get_user_exchanges(user_id: int) -> list:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT exchange FROM exchange_connections WHERE user_id = $1", user_id)
        return [r["exchange"] for r in rows]

async def save_trade(user_id: int, exchange: str, symbol: str, side: str,
                     amount: float, price: float, pnl: float, trade_date, analysis: str = None) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO trades (user_id, exchange, symbol, side, amount, price, pnl, trade_date, analysis)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, user_id, exchange, symbol, side, amount, price, pnl, trade_date, analysis)

async def get_recent_trades(user_id: int, limit: int = 10) -> list:
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM trades WHERE user_id = $1
            ORDER BY trade_date DESC LIMIT $2
        """, user_id, limit)
        return [dict(r) for r in rows]

async def delete_exchange_connection(user_id: int, exchange: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM exchange_connections WHERE user_id = $1 AND exchange = $2
        """, user_id, exchange)

# ─── Fonctions abonnement ────────────────────────────────────────

async def get_subscription(user_id: int) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM subscriptions WHERE user_id = $1", user_id)
        return dict(row) if row else None

async def create_or_update_subscription(user_id: int, plan: str,
    stripe_customer_id: str = None, stripe_subscription_id: str = None,
    status: str = "active", current_period_end=None) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO subscriptions
            (user_id, plan, stripe_customer_id, stripe_subscription_id,
             status, current_period_end, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                plan = $2,
                stripe_customer_id = COALESCE($3, subscriptions.stripe_customer_id),
                stripe_subscription_id = COALESCE($4, subscriptions.stripe_subscription_id),
                status = $5,
                current_period_end = $6,
                updated_at = NOW()
        """, user_id, plan, stripe_customer_id, stripe_subscription_id, status, current_period_end)

async def is_premium(user_id: int) -> bool:
    sub = await get_subscription(user_id)
    if not sub:
        return False
    return sub["plan"] in ["monthly", "yearly"] and sub["status"] == "active"

async def get_daily_message_count(user_id: int) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT COUNT(*) as count FROM conversations
            WHERE user_id = $1 AND role = 'user'
            AND created_at >= NOW() - INTERVAL '24 hours'
        """, user_id)
        return row["count"] if row else 0

# ─── Fonctions notifications matinales ──────────────────────────

async def set_morning_time(user_id: int, time_str: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET morning_time = $2 WHERE user_id = $1", user_id, time_str)

async def get_users_for_morning_brief(current_time: str) -> list:
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT user_id, language, level, trading_style, goal
            FROM users WHERE morning_time = $1
        """, current_time)
        return [dict(r) for r in rows]

# ─── Fonctions alertes de prix ───────────────────────────────────

async def create_price_alert(user_id: int, symbol: str, condition: str, target_price: float) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO price_alerts (user_id, symbol, condition, target_price)
            VALUES ($1, $2, $3, $4) RETURNING id
        """, user_id, symbol, condition, target_price)
        return row["id"]

async def get_user_alerts(user_id: int) -> list:
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM price_alerts WHERE user_id = $1 AND active = TRUE
            ORDER BY created_at DESC
        """, user_id)
        return [dict(r) for r in rows]

async def get_all_active_alerts() -> list:
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT pa.*, u.language FROM price_alerts pa
            JOIN users u ON u.user_id = pa.user_id
            WHERE pa.active = TRUE
        """)
        return [dict(r) for r in rows]

async def deactivate_alert(alert_id: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE price_alerts SET active = FALSE, triggered_at = NOW() WHERE id = $1
        """, alert_id)

async def delete_alert(alert_id: int, user_id: int) -> bool:
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM price_alerts WHERE id = $1 AND user_id = $2
        """, alert_id, user_id)
        return result == "DELETE 1"

# ─── Fonctions journal de trading ────────────────────────────────

async def save_journal_trade(
    user_id: int, symbol: str, side: str,
    entry_price: float, exit_price: float | None,
    amount: float, emotion: str, reason: str
) -> int:
    """Enregistre un trade dans le journal. Retourne l'id."""
    pnl = None
    pnl_pct = None
    if exit_price is not None and exit_price > 0:
        if side == "buy":
            pnl = (exit_price - entry_price) * amount
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl = (entry_price - exit_price) * amount
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO journal_trades
            (user_id, symbol, side, entry_price, exit_price, amount, emotion, reason, pnl, pnl_pct)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id
        """, user_id, symbol, side, entry_price, exit_price, amount, emotion, reason, pnl, pnl_pct)
        return row["id"]

async def get_journal_trades(user_id: int, limit: int = 20) -> list:
    """Retourne les derniers trades du journal."""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM journal_trades WHERE user_id = $1
            ORDER BY created_at DESC LIMIT $2
        """, user_id, limit)
        return [dict(r) for r in rows]

async def save_postmortem(trade_id: int, postmortem: str) -> None:
    """Sauvegarde le post-mortem IA d'un trade."""
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE journal_trades SET postmortem = $2 WHERE id = $1
        """, trade_id, postmortem)

async def delete_journal_trade(trade_id: int, user_id: int) -> bool:
    """Supprime un trade du journal."""
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM journal_trades WHERE id = $1 AND user_id = $2
        """, trade_id, user_id)
        return result == "DELETE 1"

# ─── Fonctions patterns ──────────────────────────────────────────

async def save_detected_pattern(
    user_id: int, symbol: str, timeframe: str,
    pattern_name: str, pattern_type: str,
    stars: int, neckline: float = None, target: float = None
) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO detected_patterns
            (user_id, symbol, timeframe, pattern_name, pattern_type, stars, neckline, target)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """, user_id, symbol, timeframe, pattern_name, pattern_type, stars, neckline, target)
        return row["id"]

async def get_user_patterns(user_id: int, limit: int = 10) -> list:
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM detected_patterns WHERE user_id = $1
            ORDER BY created_at DESC LIMIT $2
        """, user_id, limit)
        return [dict(r) for r in rows]
