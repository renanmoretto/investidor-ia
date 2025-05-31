import json
from pathlib import Path


def get_llm_config() -> dict[str, str] | None:
    try:
        # provider
        with open(DB_DIR / 'model.json', 'r') as f:
            model = json.load(f)

        # api key
        with open(DB_DIR / 'api_keys.json', 'r') as f:
            api_keys = json.load(f)

        return {
            'provider': model['provider'],
            'model': model['model'],
            'api_key': api_keys.get(model['provider']),
        }
    except FileNotFoundError:
        return None


PROJECT_DIR = Path(__file__).parent.parent

CACHE_DIR = PROJECT_DIR / 'cache'
CACHE_DIR.mkdir(exist_ok=True, parents=True)

DB_DIR = PROJECT_DIR / 'db'
DB_DIR.mkdir(exist_ok=True, parents=True)

# LLMs
llm_config = get_llm_config()
PROVIDER = llm_config['provider']
MODEL = llm_config['model']
API_KEY = llm_config['api_key']

# investors
INVESTORS = {
    'buffett': 'Warren Buffett',
    'graham': 'Benjamin Graham',
    'barsi': 'Luiz Barsi',
}


def reload_llm_config():
    global PROVIDER, MODEL, API_KEY
    llm_config = get_llm_config()
    PROVIDER = llm_config['provider']
    MODEL = llm_config['model']
    API_KEY = llm_config['api_key']
