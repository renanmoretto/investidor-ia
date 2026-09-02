import logging

import fitz

from agno.models.base import Model
from agno.models.anthropic import Claude
from agno.models.google.gemini import Gemini
from agno.models.openai import OpenAIChat
from agno.models.openrouter import OpenRouter


from src.settings import get_llm_config

logger = logging.getLogger(__name__)


def pdf_to_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    text = '\n'.join([page.get_text('text') for page in doc])
    return text


def pdf_bytes_to_text(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    text = '\n'.join([page.get_text('text') for page in doc])
    return text


def calc_cagr(data: dict, name: str, length: int = 5) -> float:
    """ps: data precisa estar em ordem decrescente, do mais novo para o mais antigo"""
    values = [d[name] for d in data][:length]
    cagr = (values[0] / values[-1]) ** (1 / (len(values) - 1)) - 1
    return cagr


def get_model(temperature: float = 0.3) -> Model:
    config = get_llm_config()
    provider, model, api_key = config['provider'], config['model'], config['api_key']

    if not model or not api_key:
        raise ValueError('Configure o provedor, o modelo e a chave de API no menu de configurações')

    logger.info('using llm provider=%s model=%s', provider, model)

    providers = {
        'OPENAI': OpenAIChat,
        'OPENROUTER': OpenRouter,
        'GEMINI': Gemini,
        'ANTHROPIC': Claude,
    }
    if provider not in providers:
        raise ValueError(f'Provedor {provider} não encontrado')

    return providers[provider](id=model, temperature=temperature, api_key=api_key)
