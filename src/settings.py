import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).parent.parent

CACHE_DIR = PROJECT_DIR / 'cache'
CACHE_DIR.mkdir(exist_ok=True, parents=True)

DB_DIR = PROJECT_DIR / 'db'
DB_DIR.mkdir(exist_ok=True, parents=True)

MODEL_FILE = DB_DIR / 'model.json'
API_KEYS_FILE = DB_DIR / 'api_keys.json'

PROVIDERS = ['GOOGLE', 'OPENAI', 'OPENROUTER']
DEFAULT_PROVIDER = 'GOOGLE'
DEFAULT_MODEL = 'gemini-2.0-flash'

INVESTORS = {
    'buffett': 'Warren Buffett',
    'graham': 'Benjamin Graham',
    'barsi': 'Luiz Barsi',
}


def _read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        content = path.read_text().strip()
        return json.loads(content) if content else default
    except json.JSONDecodeError:
        logger.warning('invalid json in %s, using defaults', path)
        return default


def get_api_keys() -> dict[str, str]:
    keys = _read_json(API_KEYS_FILE, {})
    return {provider: keys.get(provider) or '' for provider in PROVIDERS}


def save_api_keys(api_keys: dict[str, str]):
    API_KEYS_FILE.write_text(json.dumps(api_keys, indent=4))
    logger.info('api keys saved for providers: %s', [p for p, k in api_keys.items() if k])


def save_model(provider: str, model: str):
    MODEL_FILE.write_text(json.dumps({'provider': provider, 'model': model}, indent=4))
    logger.info('model saved: provider=%s model=%s', provider, model)


def get_llm_config() -> dict[str, str]:
    """Reads config from disk on every call, so changes take effect without a restart."""
    model = _read_json(MODEL_FILE, {'provider': DEFAULT_PROVIDER, 'model': DEFAULT_MODEL})
    provider = model.get('provider') or DEFAULT_PROVIDER
    return {
        'provider': provider,
        'model': model.get('model') or '',
        'api_key': get_api_keys().get(provider, ''),
    }


def is_configured() -> bool:
    config = get_llm_config()
    return bool(config['provider'] and config['model'] and config['api_key'])
