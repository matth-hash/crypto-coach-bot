from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import get_user, is_premium

router = Router()

@router.message(Command("help"))
async def cmd_help(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "en"
    premium = await is_premium(user_id)

    plan_texts = {
        "fr": "💎 Premium" if premium else "🆓 Gratuit (5 msg/jour)",
        "en": "💎 Premium" if premium else "🆓 Free (5 msg/day)",
        "es": "💎 Premium" if premium else "🆓 Gratuito (5 msg/día)",
        "pt": "💎 Premium" if premium else "🆓 Gratuito (5 msg/dia)",
    }

    help_texts = {
        "fr": (
            "❓ *Aide TradeCoach AI*\n\n"
            f"📋 Ton plan : {plan_texts['fr']}\n\n"
            "─────────────────\n"
            "👤 *Profil & Progression*\n"
            "/profil — Voir ton profil complet\n"
            "/niveau — Ton niveau et XP\n"
            "/badges — Tes badges obtenus\n"
            "/reset — Réinitialiser ton profil\n\n"
            "─────────────────\n"
            "📊 *Trading & Analyse*\n"
            "/exchange — Connecter Binance, Bybit...\n"
            "/trades — Analyser tes trades récents\n\n"
            "─────────────────\n"
            "🧠 *Psychologie*\n"
            "/psycho — Rapport de tes biais\n"
            "/check — Vérification comportementale\n\n"
            "─────────────────\n"
            "📓 *Journal*\n"
            "/journal — Journal de trading + post-mortem IA\n\n"
            "─────────────────\n"
            "🔔 *Notifications & Alertes*\n"
            "/morning — 🌅 Brief marché quotidien\n"
            "/score — 📊 Score de marché en temps réel\n"
            "/alerte — Créer une alerte de prix\n"
            "/alertes — Gérer tes alertes actives\n\n"
            "─────────────────\n"
            "📚 *Éducation*\n"
            "/lexique — Termes de trading expliqués\n\n"
            "─────────────────\n"
            "💎 *Premium*\n"
            "/premium — Voir les offres\n"
            "/activate — Activer après paiement\n\n"
            "─────────────────\n"
            "💬 *Coaching IA*\n"
            "Envoie n'importe quel message pour\n"
            "discuter avec ton coach IA personnel !\n\n"
            "📈 *Prix en temps réel inclus*\n"
            "BTC, ETH, SOL, Or, Argent et plus encore."
        ),
        "en": (
            "❓ *TradeCoach AI Help*\n\n"
            f"📋 Your plan: {plan_texts['en']}\n\n"
            "─────────────────\n"
            "👤 *Profile & Progress*\n"
            "/profil — View your full profile\n"
            "/niveau — Your level and XP\n"
            "/badges — Your earned badges\n"
            "/reset — Reset your profile\n\n"
            "─────────────────\n"
            "📊 *Trading & Analysis*\n"
            "/exchange — Connect Binance, Bybit...\n"
            "/trades — Analyze your recent trades\n\n"
            "─────────────────\n"
            "🧠 *Psychology*\n"
            "/psycho — Your bias report\n"
            "/check — Behavioral check\n\n"
            "─────────────────\n"
            "📓 *Journal*\n"
            "/journal — Trading journal + AI post-mortem\n\n"
            "─────────────────\n"
            "🔔 *Notifications & Alerts*\n"
            "/morning — 🌅 Daily market brief\n"
            "/score — 📊 Real-time market score\n"
            "/alerte — Create a price alert\n"
            "/alertes — Manage your active alerts\n\n"
            "─────────────────\n"
            "📚 *Education*\n"
            "/lexique — Trading terms explained\n\n"
            "─────────────────\n"
            "💎 *Premium*\n"
            "/premium — View plans\n"
            "/activate — Activate after payment\n\n"
            "─────────────────\n"
            "💬 *AI Coaching*\n"
            "Send any message to chat with\n"
            "your personal AI coach!\n\n"
            "📈 *Real-time prices included*\n"
            "BTC, ETH, SOL, Gold, Silver and more."
        ),
        "es": (
            "❓ *Ayuda TradeCoach AI*\n\n"
            f"📋 Tu plan: {plan_texts['es']}\n\n"
            "─────────────────\n"
            "👤 *Perfil y Progreso*\n"
            "/profil — Ver tu perfil completo\n"
            "/nivel — Tu nivel y XP\n"
            "/badges — Tus insignias\n"
            "/reset — Reiniciar tu perfil\n\n"
            "─────────────────\n"
            "📊 *Trading y Análisis*\n"
            "/exchange — Conectar Binance, Bybit...\n"
            "/trades — Analizar tus trades recientes\n\n"
            "─────────────────\n"
            "🧠 *Psicología*\n"
            "/psycho — Informe de sesgos\n"
            "/check — Verificación conductual\n\n"
            "─────────────────\n"
            "📓 *Diario*\n"
            "/journal — Diario de trading + post-mortem IA\n\n"
            "─────────────────\n"
            "🔔 *Notificaciones y Alertas*\n"
            "/morning — 🌅 Brief diario del mercado\n"
            "/score — 📊 Score del mercado en tiempo real\n"
            "/alerte — Crear una alerta de precio\n"
            "/alertes — Gestionar alertas activas\n\n"
            "─────────────────\n"
            "📚 *Educación*\n"
            "/lexique — Términos de trading explicados\n\n"
            "─────────────────\n"
            "💎 *Premium*\n"
            "/premium — Ver planes\n"
            "/activate — Activar tras el pago\n\n"
            "─────────────────\n"
            "💬 *Coaching IA*\n"
            "¡Envía cualquier mensaje para hablar\n"
            "con tu coach IA personal!\n\n"
            "📈 *Precios en tiempo real incluidos*\n"
            "BTC, ETH, SOL, Oro, Plata y más."
        ),
        "pt": (
            "❓ *Ajuda TradeCoach AI*\n\n"
            f"📋 Seu plano: {plan_texts['pt']}\n\n"
            "─────────────────\n"
            "👤 *Perfil e Progresso*\n"
            "/profil — Ver seu perfil completo\n"
            "/nivel — Seu nível e XP\n"
            "/badges — Suas conquistas\n"
            "/reset — Redefinir seu perfil\n\n"
            "─────────────────\n"
            "📊 *Trading e Análise*\n"
            "/exchange — Conectar Binance, Bybit...\n"
            "/trades — Analisar seus trades recentes\n\n"
            "─────────────────\n"
            "🧠 *Psicologia*\n"
            "/psycho — Relatório de vieses\n"
            "/check — Verificação comportamental\n\n"
            "─────────────────\n"
            "📓 *Diário*\n"
            "/journal — Diário de trading + post-mortem IA\n\n"
            "─────────────────\n"
            "🔔 *Notificações e Alertas*\n"
            "/morning — 🌅 Brief diário do mercado\n"
            "/score — 📊 Score do mercado em tempo real\n"
            "/alerte — Criar um alerta de preço\n"
            "/alertes — Gerenciar alertas ativos\n\n"
            "─────────────────\n"
            "📚 *Educação*\n"
            "/lexique — Termos de trading explicados\n\n"
            "─────────────────\n"
            "💎 *Premium*\n"
            "/premium — Ver planos\n"
            "/activate — Ativar após pagamento\n\n"
            "─────────────────\n"
            "💬 *Coaching IA*\n"
            "Envie qualquer mensagem para conversar\n"
            "com seu coach IA pessoal!\n\n"
            "📈 *Preços em tempo real incluídos*\n"
            "BTC, ETH, SOL, Ouro, Prata e mais."
        ),
    }

    builder = InlineKeyboardBuilder()

    if not premium:
        upgrade_labels = {
            "fr": "💎 Passer Premium",
            "en": "💎 Upgrade to Premium",
            "es": "💎 Actualizar a Premium",
            "pt": "💎 Upgrade para Premium",
        }
        builder.button(
            text=upgrade_labels.get(lang, upgrade_labels["en"]),
            callback_data="show_premium"
        )

    builder.button(
        text={"fr": "📊 Analyser mes trades", "en": "📊 Analyze my trades",
              "es": "📊 Analizar mis trades", "pt": "📊 Analisar meus trades"}.get(lang, "📊 Analyze my trades"),
        callback_data="show_trades"
    )
    builder.adjust(1)

    await message.answer(
        help_texts.get(lang, help_texts["en"]),
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@router.message(Command("niveau"))
async def cmd_niveau_alias(message: Message):
    from bot.gamification_handlers import cmd_level
    await cmd_level(message)
