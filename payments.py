import stripe
import os
from datetime import datetime, timezone

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

PRICE_MONTHLY = os.environ.get("STRIPE_PRICE_MONTHLY")
PRICE_YEARLY = os.environ.get("STRIPE_PRICE_YEARLY")

FREE_DAILY_LIMIT = 5  # Messages gratuits par jour

async def create_checkout_session(
    user_id: int,
    plan: str,
    lang: str
) -> str | None:
    """Crée une session de paiement Stripe et retourne l'URL."""

    price_id = PRICE_MONTHLY if plan == "monthly" else PRICE_YEARLY

    success_urls = {
        "fr": f"https://t.me/TradeCoach_ai_bot?start=success",
        "en": f"https://t.me/TradeCoach_ai_bot?start=success",
        "es": f"https://t.me/TradeCoach_ai_bot?start=success",
        "pt": f"https://t.me/TradeCoach_ai_bot?start=success",
    }

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_urls.get(lang, success_urls["en"]),
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