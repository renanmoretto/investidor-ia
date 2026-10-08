import logging

from src import db

logger = logging.getLogger(__name__)

PROVIDERS = ['OPENAI', 'OPENROUTER', 'GEMINI', 'ANTHROPIC']
DEFAULT_PROVIDER = 'OPENAI'
DEFAULT_MODEL = ''

INVESTORS = {
    'buffett': 'Warren Buffett',
    'graham': 'Benjamin Graham',
    'barsi': 'Luiz Barsi',
    'lynch': 'Peter Lynch',
    'greenblatt': 'Joel Greenblatt',
}


def get_api_keys() -> dict[str, str]:
    keys = db.get_api_keys()
    return {provider: keys.get(provider) or '' for provider in PROVIDERS}


def save_api_key(provider: str, api_key: str):
    db.set_api_key(provider, api_key)
    logger.info('api key saved for provider=%s', provider)


def save_model(provider: str, model: str):
    db.set_setting('provider', provider)
    db.set_setting('model', model)
    logger.info('model saved: provider=%s model=%s', provider, model)


def get_llm_config() -> dict[str, str]:
    """Reads config from the database on every call, so changes take effect without a restart."""
    provider = db.get_setting('provider') or DEFAULT_PROVIDER
    return {
        'provider': provider,
        'model': db.get_setting('model') or DEFAULT_MODEL,
        'api_key': get_api_keys().get(provider, ''),
    }


def is_configured() -> bool:
    config = get_llm_config()
    return bool(config['provider'] and config['model'] and config['api_key'])
