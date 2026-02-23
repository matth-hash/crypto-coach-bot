import os

# Tokens
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("telegram_token")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("anthropic_api_key")

# Langues supportées
SUPPORTED_LANGUAGES = ["fr", "en", "es", "pt"]
DEFAULT_LANGUAGE = "en"

# Mapping codes Telegram → nos langues
LANGUAGE_MAP = {
    "fr": "fr", "en": "en", "es": "es", "pt": "pt",
    "pt-br": "pt", "pt-BR": "pt"
}

def detect_language(telegram_lang_code: str) -> str:
    if not telegram_lang_code:
        return DEFAULT_LANGUAGE
    lang = telegram_lang_code.lower()
    if lang in LANGUAGE_MAP:
        return LANGUAGE_MAP[lang]
    prefix = lang.split("-")[0]
    if prefix in SUPPORTED_LANGUAGES:
        return prefix
    return DEFAULT_LANGUAGE