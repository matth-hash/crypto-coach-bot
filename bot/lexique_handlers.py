from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_user

router = Router()

LEXIQUE = {
    "scalping": ("⚡ Scalping", "Style de trading ultra-rapide : acheter et revendre en quelques secondes ou minutes pour cumuler de petits profits répétés."),
    "day_trading": ("☀️ Day Trading", "Ouvrir et clôturer ses trades dans la même journée. Aucune position gardée la nuit."),
    "swing_trading": ("🌊 Swing Trading", "Garder ses positions plusieurs jours ou semaines pour profiter de variations de prix plus importantes."),
    "hodl": ("🏦 HODLer", "De 'HOLD' (tenir). Acheter des cryptos et les conserver sur le long terme sans s'inquiéter des fluctuations quotidiennes."),
    "dca": ("📊 DCA", "'Dollar Cost Averaging' : investir régulièrement une somme fixe peu importe le prix. Réduit le risque de mal timing."),
    "fomo": ("💥 FOMO", "'Fear Of Missing Out' : peur de rater une opportunité, qui pousse à acheter impulsivement quand les prix montent fort."),
    "fud": ("📉 FUD", "'Fear, Uncertainty, Doubt' : rumeurs négatives qui créent la peur et poussent les gens à vendre."),
    "fear_greed": ("😱 Fear & Greed Index", "Indicateur de 0 à 100 mesurant l'émotion du marché. 0 = peur extrême, 100 = avidité extrême."),
    "chandelier": ("🕯️ Chandelier", "Représentation graphique du prix : montre l'ouverture, la fermeture, le plus haut et le plus bas sur une période."),
    "stop_loss": ("📉 Stop Loss", "Ordre automatique qui vend si le prix descend trop bas. Protège contre les grosses pertes."),
    "take_profit": ("🎯 Take Profit", "Ordre automatique qui vend quand le prix atteint un objectif. Sécurise les gains."),
    "rsi": ("📊 RSI", "'Relative Strength Index' : indicateur 0-100. Sous 30 = potentiellement survendu. Au-dessus de 70 = potentiellement suracheté."),
    "exchange": ("🔗 Exchange", "Plateforme pour acheter et vendre des cryptos (ex: Binance, Kraken, Coinbase)."),
    "api": ("🔑 Clé API", "Code d'accès permettant au bot de lire tes données sur un exchange, sans pouvoir toucher à ton argent."),
    "altcoin": ("📊 Altcoin", "Toute cryptomonnaie autre que le Bitcoin. ETH, SOL, BNB, XRP sont des altcoins."),
    "stablecoin": ("⚖️ Stablecoin", "Crypto dont la valeur est stable, indexée sur le dollar (ex: USDT, USDC). Permet de se mettre en sécurité."),
    "baleine": ("🐋 Baleine (Whale)", "Grand investisseur possédant une quantité énorme de cryptos, capable d'influencer les prix."),
    "bullish": ("📈 Bullish", "Le marché est en hausse ou on anticipe une hausse. Sentiment positif."),
    "bearish": ("📉 Bearish", "Le marché est en baisse ou on anticipe une baisse. Sentiment négatif."),
    "portfolio": ("💰 Portfolio", "L'ensemble de tes positions et investissements crypto."),
}

def get_lexique_keyboard(lang="fr"):
    builder = InlineKeyboardBuilder()
    labels = {
        "fr": [
            ("⚡ Scalping", "lex_scalping"),
            ("☀️ Day Trading", "lex_day_trading"),
            ("🌊 Swing Trading", "lex_swing_trading"),
            ("🏦 HODLer", "lex_hodl"),
            ("📊 DCA", "lex_dca"),
            ("💥 FOMO", "lex_fomo"),
            ("📉 FUD", "lex_fud"),
            ("😱 Fear & Greed", "lex_fear_greed"),
            ("🕯️ Chandelier", "lex_chandelier"),
            ("📉 Stop Loss", "lex_stop_loss"),
            ("🎯 Take Profit", "lex_take_profit"),
            ("📊 RSI", "lex_rsi"),
            ("🔗 Exchange", "lex_exchange"),
            ("🔑 Clé API", "lex_api"),
            ("🐋 Baleine", "lex_baleine"),
            ("📈 Bullish / Bearish", "lex_bullish"),
        ]
    }
    for text, data in labels.get(lang, labels["fr"]):
        builder.button(text=text, callback_data=data)
    builder.adjust(2)
    return builder.as_markup()

@router.message(Command("lexique"))
async def cmd_lexique(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    lang = user["language"] if user else "fr"

    texts = {
        "fr": "📚 *Lexique Trading*\n\nClique sur un terme pour sa définition :",
        "en": "📚 *Trading Glossary*\n\nTap a term for its definition:",
        "es": "📚 *Glosario de Trading*\n\nToca un término para ver su definición:",
        "pt": "📚 *Glossário de Trading*\n\nClique em um termo para ver sua definição:",
    }

    await message.answer(
        texts.get(lang, texts["fr"]),
        reply_markup=get_lexique_keyboard(lang),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("lex_"))
async def cb_lexique_term(callback: CallbackQuery):
    key = callback.data.replace("lex_", "")
    if key not in LEXIQUE:
        await callback.answer("Terme non trouvé", show_alert=True)
        return

    title, definition = LEXIQUE[key]
    await callback.message.answer(
        f"*{title}*\n\n{definition}",
        parse_mode="Markdown"
    )
    await callback.answer()
