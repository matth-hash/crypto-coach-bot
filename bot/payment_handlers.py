from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import (
    get_user, is_premium, get_subscription,
    create_or_update_subscription, get_daily_message_count
)
from payments import create_checkout_session, FREE_DAILY_LIMIT

router = Router()

# ─── /premium ────────────────────────────────────────────────────

@router.message(Command("premium"))
async def cmd_premium(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "en"

    premium = await is_premium(user_id)

    if premium:
        sub = await get_subscription(user_id)
        end_date = sub.get("current_period_end")
        date_str = end_date.strftime("%d/%m/%Y") if end_date else "—"

        already_texts = {
            "fr": (
                f"✅ *Tu es déjà Premium !*\n\n"
                f"📅 Renouvellement : {date_str}\n\n"
                f"Tu as accès à toutes les fonctionnalités sans limite."
            ),
            "en": (
                f"✅ *You are already Premium!*\n\n"
                f"📅 Renewal: {date_str}\n\n"
                f"You have access to all features without limit."
            ),
            "es": (
                f"✅ *¡Ya eres Premium!*\n\n"
                f"📅 Renovación: {date_str}\n\n"
                f"Tienes acceso a todas las funciones sin límite."
            ),
            "pt": (
                f"✅ *Você já é Premium!*\n\n"
                f"📅 Renovação: {date_str}\n\n"
                f"Você tem acesso a todas as funcionalidades sem limite."
            ),
        }
        await message.answer(
            already_texts.get(lang, already_texts["en"]),
            parse_mode="Markdown"
        )
        return

    # Afficher les offres
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📅 Mensuel — 9.99€/mois" if lang == "fr"
        else "📅 Monthly — €9.99/month" if lang == "en"
        else "📅 Mensual — 9.99€/mes" if lang == "es"
        else "📅 Mensal — €9.99/mês",
        callback_data="subscribe:monthly"
    )
    builder.button(
        text="🎯 Annuel — 79.99€/an (-33%)" if lang == "fr"
        else "🎯 Yearly — €79.99/year (-33%)" if lang == "en"
        else "🎯 Anual — 79.99€/año (-33%)" if lang == "es"
        else "🎯 Anual — €79.99/ano (-33%)",
        callback_data="subscribe:yearly"
    )
    builder.adjust(1)

    offers = {
        "fr": (
            "💎 *CryptoCoach Premium*\n\n"
            "*Gratuit :*\n"
            f"• {FREE_DAILY_LIMIT} messages par jour\n"
            "• Coaching IA de base\n"
            "• Profil et niveaux\n\n"
            "*Premium :*\n"
            "• ✅ Messages illimités\n"
            "• ✅ Analyse de trades exchange\n"
            "• ✅ Rapport psychologique complet\n"
            "• ✅ Circuit breaker comportemental\n"
            "• ✅ Priorité de réponse\n"
            "• ✅ Accès aux futures fonctionnalités\n\n"
            "Choisis ton offre :"
        ),
        "en": (
            "💎 *CryptoCoach Premium*\n\n"
            "*Free:*\n"
            f"• {FREE_DAILY_LIMIT} messages per day\n"
            "• Basic AI coaching\n"
            "• Profile and levels\n\n"
            "*Premium:*\n"
            "• ✅ Unlimited messages\n"
            "• ✅ Exchange trade analysis\n"
            "• ✅ Full psychological report\n"
            "• ✅ Behavioral circuit breaker\n"
            "• ✅ Priority response\n"
            "• ✅ Access to future features\n\n"
            "Choose your plan:"
        ),
        "es": (
            "💎 *CryptoCoach Premium*\n\n"
            "*Gratis:*\n"
            f"• {FREE_DAILY_LIMIT} mensajes por día\n"
            "• Coaching IA básico\n"
            "• Perfil y niveles\n\n"
            "*Premium:*\n"
            "• ✅ Mensajes ilimitados\n"
            "• ✅ Análisis de trades exchange\n"
            "• ✅ Informe psicológico completo\n"
            "• ✅ Circuit breaker conductual\n"
            "• ✅ Respuesta prioritaria\n"
            "• ✅ Acceso a futuras funciones\n\n"
            "Elige tu plan:"
        ),
        "pt": (
            "💎 *CryptoCoach Premium*\n\n"
            "*Gratuito:*\n"
            f"• {FREE_DAILY_LIMIT} mensagens por dia\n"
            "• Coaching IA básico\n"
            "• Perfil e níveis\n\n"
            "*Premium:*\n"
            "• ✅ Mensagens ilimitadas\n"
            "• ✅ Análise de trades exchange\n"
            "• ✅ Relatório psicológico completo\n"
            "• ✅ Circuit breaker comportamental\n"
            "• ✅ Resposta prioritária\n"
            "• ✅ Acesso a futuras funcionalidades\n\n"
            "Escolha seu plano:"
        ),
    }

    await message.answer(
        offers.get(lang, offers["en"]),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("subscribe:"))
async def process_subscribe(callback: CallbackQuery):
    plan = callback.data.split(":")[1]
    user_id = callback.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "en"

    loading_texts = {
        "fr": "🔄 Création du lien de paiement...",
        "en": "🔄 Creating payment link...",
        "es": "🔄 Creando enlace de pago...",
        "pt": "🔄 Criando link de pagamento...",
    }
    await callback.message.edit_text(
        loading_texts.get(lang, loading_texts["en"])
    )

    checkout_url = await create_checkout_session(user_id, plan, lang)

    if not checkout_url:
        error_texts = {
            "fr": "❌ Erreur lors de la création du paiement. Réessaie plus tard.",
            "en": "❌ Error creating payment. Please try again later.",
            "es": "❌ Error al crear el pago. Inténtalo más tarde.",
            "pt": "❌ Erro ao criar pagamento. Tente novamente mais tarde.",
        }
        await callback.message.edit_text(
            error_texts.get(lang, error_texts["en"])
        )
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    builder.button(
        text="💳 Payer maintenant" if lang == "fr"
        else "💳 Pay now" if lang == "en"
        else "💳 Pagar ahora" if lang == "es"
        else "💳 Pagar agora",
        url=checkout_url
    )

    payment_texts = {
        "fr": (
            "✅ *Lien de paiement prêt !*\n\n"
            "Clique sur le bouton ci-dessous pour finaliser ton abonnement.\n"
            "Après le paiement, envoie /activate pour activer ton compte Premium."
        ),
        "en": (
            "✅ *Payment link ready!*\n\n"
            "Click the button below to complete your subscription.\n"
            "After payment, send /activate to activate your Premium account."
        ),
        "es": (
            "✅ *¡Enlace de pago listo!*\n\n"
            "Haz clic en el botón de abajo para completar tu suscripción.\n"
            "Después del pago, envía /activate para activar tu cuenta Premium."
        ),
        "pt": (
            "✅ *Link de pagamento pronto!*\n\n"
            "Clique no botão abaixo para finalizar sua assinatura.\n"
            "Após o pagamento, envie /activate para ativar sua conta Premium."
        ),
    }

    await callback.message.edit_text(
        payment_texts.get(lang, payment_texts["en"]),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

# ─── /activate ───────────────────────────────────────────────────

@router.message(Command("activate"))
async def cmd_activate(message: Message):
    """
    Commande temporaire pour activer manuellement le premium
    en attendant les webhooks Stripe.
    """
    user_id = message.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "en"

    from datetime import timedelta, datetime

    end_date = datetime.utcnow() + timedelta(days=30)
    await create_or_update_subscription(
        user_id, "monthly", status="active",
        current_period_end=end_date
    )

    activated_texts = {
        "fr": (
            "✅ *Compte Premium activé !*\n\n"
            "Tu as maintenant accès à toutes les fonctionnalités sans limite.\n"
            "Merci pour ta confiance ! 🚀"
        ),
        "en": (
            "✅ *Premium account activated!*\n\n"
            "You now have access to all features without limit.\n"
            "Thank you for your trust! 🚀"
        ),
        "es": (
            "✅ *¡Cuenta Premium activada!*\n\n"
            "Ahora tienes acceso a todas las funciones sin límite.\n"
            "¡Gracias por tu confianza! 🚀"
        ),
        "pt": (
            "✅ *Conta Premium ativada!*\n\n"
            "Agora você tem acesso a todas as funcionalidades sem limite.\n"
            "Obrigado pela sua confiança! 🚀"
        ),
    }

    await message.answer(
        activated_texts.get(lang, activated_texts["en"]),
        parse_mode="Markdown"
    )

# ─── Vérification limite freemium ────────────────────────────────

async def check_free_limit(message: Message, lang: str) -> bool:
    """
    Vérifie si l'utilisateur gratuit a atteint sa limite.
    Retourne True si l'utilisateur peut continuer, False sinon.
    """
    user_id = message.from_user.id

    if await is_premium(user_id):
        return True

    count = await get_daily_message_count(user_id)

    if count >= FREE_DAILY_LIMIT:
        limit_texts = {
            "fr": (
                f"⚠️ *Limite journalière atteinte*\n\n"
                f"Tu as utilisé tes {FREE_DAILY_LIMIT} messages gratuits aujourd'hui.\n\n"
                "Passe en *Premium* pour des messages illimités !\n"
                "👉 /premium"
            ),
            "en": (
                f"⚠️ *Daily limit reached*\n\n"
                f"You've used your {FREE_DAILY_LIMIT} free messages today.\n\n"
                "Upgrade to *Premium* for unlimited messages!\n"
                "👉 /premium"
            ),
            "es": (
                f"⚠️ *Límite diario alcanzado*\n\n"
                f"Has usado tus {FREE_DAILY_LIMIT} mensajes gratuitos hoy.\n\n"
                "¡Pasa a *Premium* para mensajes ilimitados!\n"
                "👉 /premium"
            ),
            "pt": (
                f"⚠️ *Limite diário atingido*\n\n"
                f"Você usou suas {FREE_DAILY_LIMIT} mensagens gratuitas hoje.\n\n"
                "Passe para *Premium* para mensagens ilimitadas!\n"
                "👉 /premium"
            ),
        }
        await message.answer(
            limit_texts.get(lang, limit_texts["en"]),
            parse_mode="Markdown"
        )
        return False

    return True