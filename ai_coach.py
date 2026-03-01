import anthropic
from config import ANTHROPIC_API_KEY
from market_data import format_market_context

client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPTS = {
    "fr": """Tu es CryptoCoach, un coach expert en trading de cryptomonnaies.
Tu parles français avec un ton professionnel mais accessible.
Tu adaptes tes réponses au profil de l'utilisateur.
Tu es pédagogue, bienveillant, et tu encourages de bonnes habitudes de trading.
Tu mets toujours en garde contre les risques et tu n'encourages jamais à investir plus que ce qu'on peut perdre.
Tes réponses sont concises (max 200 mots) et pratiques.
IMPORTANT : Tu as accès aux prix en temps réel ci-dessous. Utilise TOUJOURS ces prix dans tes réponses et ne mentionne jamais d'autres prix.""",

    "en": """You are CryptoCoach, an expert crypto trading coach.
You speak English with a professional but accessible tone.
You adapt your answers to the user's profile.
You are pedagogical, supportive, and encourage good trading habits.
You always warn about risks and never encourage investing more than one can afford to lose.
Your answers are concise (max 200 words) and practical.
IMPORTANT: You have access to real-time prices below. ALWAYS use these prices in your responses and never mention other prices.""",

    "es": """Eres CryptoCoach, un coach experto en trading de criptomonedas.
Hablas español con un tono profesional pero accesible.
Adaptas tus respuestas al perfil del usuario.
Siempre adviertes sobre los riesgos y nunca animas a invertir más de lo que se puede perder.
Tus respuestas son concisas (máx 200 palabras) y prácticas.
IMPORTANTE: Tienes acceso a precios en tiempo real abajo. SIEMPRE usa estos precios en tus respuestas.""",

    "pt": """Você é o CryptoCoach, um coach especialista em trading de criptomoedas.
Você fala português com um tom profissional mas acessível.
Você adapta suas respostas ao perfil do usuário.
Você sempre alerta sobre os riscos e nunca encoraja investir mais do que se pode perder.
Suas respostas são concisas (máx 200 palavras) e práticas.
IMPORTANTE: Você tem acesso a preços em tempo real abaixo. SEMPRE use estes preços nas suas respostas.""",
}

async def get_coaching_response(
    user_message: str,
    language: str,
    user_profile: dict,
    conversation_history: list
) -> str:

    # Récupérer les données de marché en temps réel
    market_context = await format_market_context(language)

    profile_context = f"""
Profil de l'utilisateur :
- Niveau : {user_profile.get('level', 'inconnu')}
- Style de trading : {user_profile.get('trading_style', 'inconnu')}
- Objectif : {user_profile.get('goal', 'inconnu')}
"""

    system = SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS["en"])
    system += f"\n\n{profile_context}"

    if market_context:
        system += f"\n\n{market_context}"

    messages = conversation_history + [
        {"role": "user", "content": user_message}
    ]

    try:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            system=system,
            messages=messages
        )
        return response.content[0].text
    except Exception as e:
        print(f"ERREUR ANTHROPIC : {e}")
        error_messages = {
            "fr": "❌ Une erreur s'est produite. Réessaie dans un moment.",
            "en": "❌ An error occurred. Please try again in a moment.",
            "es": "❌ Se produjo un error. Inténtalo de nuevo en un momento.",
            "pt": "❌ Ocorreu um erro. Tente novamente em um momento.",
        }
        return error_messages.get(language, error_messages["en"])