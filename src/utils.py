import fitz

from agno.models.base import Model
from agno.models.google.gemini import Gemini
from agno.models.openai import OpenAIChat
from agno.models.openrouter import OpenRouter


from src.settings import PROVIDER, MODEL, API_KEY


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
    if PROVIDER == 'GOOGLE':
        return Gemini(id=MODEL, temperature=temperature, api_key=API_KEY)
    elif PROVIDER == 'OPENAI':
        return OpenAIChat(id=MODEL, temperature=temperature, api_key=API_KEY)
    elif PROVIDER == 'OPENROUTER':
        return OpenRouter(id=MODEL, temperature=temperature, api_key=API_KEY)
    else:
        raise ValueError(f'Modelo {MODEL} não encontrado')
