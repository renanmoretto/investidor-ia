import json
from pathlib import Path


def _get_api_key(provider: str) -> str | None:
    try:
        with open(DB_DIR / 'api_keys.json', 'r') as f:
            api_keys = json.load(f)
        return api_keys.get(provider)
    except FileNotFoundError:
        return None


PROJECT_DIR = Path(__file__).parent.parent

CACHE_DIR = PROJECT_DIR / 'cache'
CACHE_DIR.mkdir(exist_ok=True, parents=True)

DB_DIR = PROJECT_DIR / 'db'
DB_DIR.mkdir(exist_ok=True, parents=True)

# api keys
GEMINI_API_KEY = _get_api_key('gemini')

# investors
INVESTORS = {
    'buffett': 'Warren Buffett',
    'graham': 'Benjamin Graham',
    'barsi': 'Luiz Barsi',
}


def reload_api_keys():
    global GEMINI_API_KEY
    GEMINI_API_KEY = _get_api_key('gemini')
