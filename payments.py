import stripe
import os
import json
from datetime import datetime, timezone
from aiohttp import web
from database import create_or_update_subscription

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
PRICE_MONTHLY = os.environ.get("STRIPE_PRICE_MONTHLY")
PRICE_YEARLY = os.environ.get("STRIPE_PRICE_YEARLY")
FREE_DAILY_LIMIT = 5

# ─── Checkout ────────────────────────────────────────────────────

async def create_checkout_session(user_id: int, plan: str, lang: str) -> str | None:
    """Crée une session de paiement Stripe et retourne l'URL."""
    price_id = PRICE_MONTHLY if plan == "monthly" else PRICE_YEARLY
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url="https://t.me/TradeCoach_ai_bot?start=success",
            cancel_url="https://t.me/TradeCoach_ai_bot",
            metadata={"user_id": str(user_id), "plan": plan},
            allow_promotion_codes=True,
        )
        return session.url
    except Exception as e:
        print(f"Erreur Stripe checkout: {e}")
        return None

def get_subscription_status(stripe_subscription_id: str) -> dict | None:
    """Vérifie le statut d'un abonnement Stripe."""
    try:
        sub = stripe.Subscription.retrieve(stripe_subscription_id)
        return {
            "status": sub.status,
            "current_period_end": datetime.fromtimestamp(
                sub.current_period_end, tz=timezone.utc
            ),
        }
    except Exception as e:
        print(f"Erreur Stripe status: {e}")
        return None

# ─── Webhook ─────────────────────────────────────────────────────

async def handle_stripe_webhook(request: web.Request) -> web.Response:
    """Endpoint aiohttp qui reçoit les événements Stripe."""
    payload = await request.read()
    sig_header = request.headers.get("Stripe-Signature", "")

    # Vérification de la signature Stripe
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        print("❌ Webhook signature invalide")
        return web.Response(status=400, text="Invalid signature")
    except Exception as e:
        print(f"❌ Erreur webhook: {e}")
        return web.Response(status=400, text=str(e))

    event_type = event["type"]
    data = event["data"]["object"]

    # ── Paiement réussi → activation premium ──
    if event_type == "checkout.session.completed":
        user_id = int(data.get("metadata", {}).get("user_id", 0))
        plan = data.get("metadata", {}).get("plan", "monthly")
        stripe_customer_id = data.get("customer")
        stripe_subscription_id = data.get("subscription")

        if user_id:
            # Récupère la date de fin de période
            current_period_end = None
            if stripe_subscription_id:
                try:
                    sub = stripe.Subscription.retrieve(stripe_subscription_id)
                    current_period_end = datetime.fromtimestamp(
                        sub.current_period_end, tz=timezone.utc
                    )
                except Exception:
                    pass

            await create_or_update_subscription(
                user_id=user_id,
                plan=plan,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
                status="active",
                current_period_end=current_period_end,
            )
            print(f"✅ Premium activé pour user {user_id} ({plan})")

    # ── Abonnement annulé ou expiré → retour gratuit ──
    elif event_type in ("customer.subscription.deleted", "customer.subscription.paused"):
        stripe_subscription_id = data.get("id")
        stripe_customer_id = data.get("customer")

        # Retrouve le user via stripe_customer_id
        try:
            from database import pool
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT user_id FROM subscriptions WHERE stripe_customer_id = $1",
                    stripe_customer_id
                )
                if row:
                    await create_or_update_subscription(
                        user_id=row["user_id"],
                        plan="free",
                        status="canceled",
                    )
                    print(f"⬇️ Premium annulé pour user {row['user_id']}")
        except Exception as e:
            print(f"Erreur annulation subscription: {e}")

    # ── Renouvellement réussi ──
    elif event_type == "invoice.payment_succeeded":
        stripe_subscription_id = data.get("subscription")
        stripe_customer_id = data.get("customer")

        if stripe_subscription_id:
            try:
                sub = stripe.Subscription.retrieve(stripe_subscription_id)
                current_period_end = datetime.fromtimestamp(
                    sub.current_period_end, tz=timezone.utc
                )
                from database import pool
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT user_id, plan FROM subscriptions WHERE stripe_customer_id = $1",
                        stripe_customer_id
                    )
                    if row:
                        await create_or_update_subscription(
                            user_id=row["user_id"],
                            plan=row["plan"],
                            status="active",
                            current_period_end=current_period_end,
                        )
                        print(f"🔄 Renouvellement premium pour user {row['user_id']}")
            except Exception as e:
                print(f"Erreur renouvellement: {e}")

    return web.Response(status=200, text="OK")

# ─── Serveur webhook aiohttp ─────────────────────────────────────

async def start_webhook_server():
    """Lance le serveur HTTP pour recevoir les webhooks Stripe."""
    app = web.Application()
    app.router.add_post("/webhook/stripe", handle_stripe_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("✅ Serveur webhook Stripe démarré sur :8080")
