import fitz

from agno.models.base import Model
from agno.models.google.gemini import Gemini
from agno.models.openai import OpenAIChat


from src.settings import get_api_key


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


def get_model(model_name: str = 'gemini-2.0-flash', provider: str = 'gemini', temperature: float = 0.3) -> Model:
    if provider == 'gemini':
        return Gemini(id=model_name, temperature=temperature, api_key=get_api_key('gemini'))
    elif provider == 'openai':
        return OpenAIChat(id=model_name, temperature=temperature, api_key=get_api_key('openai'))
    else:
        raise ValueError(f'Modelo {model_name} não encontrado')
