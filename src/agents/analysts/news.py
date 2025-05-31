import time
from typing import TypedDict

import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from agno.agent import Agent

from src.utils import get_model
from src.agents.base import BaseAgentOutput
from src.data import stocks


class News(TypedDict):
    title: str
    url: str
    body: str
    content: str


def _search_news_einvestidor(ticker: str, company_name: str) -> list[News]:
    results = DDGS().text(
        f'notícias sobre a empresa {company_name} (ticker {ticker}) site:einvestidor.estadao.com.br',
        max_results=5,
        region='br-pt',
        timelimit='3m',
    )

    news = []
    for result in results:
        url = result['href']
        if '/tag/' in url:
            continue
        r = requests.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        soup_content = soup.find('div', class_='content-editor')
        content = soup_content.text if soup_content else 'Conteúdo não encontrado'
        news.append({'title': result['title'], 'url': url, 'body': result['body'], 'content': content})
        time.sleep(1)

    return news


def analyze(ticker: str) -> BaseAgentOutput:
    company_name = stocks.name(ticker)
    news = _search_news_einvestidor(ticker, company_name)

    prompt = f"""
    Você é um analista especializado em pesquisar e analisar notícias sobre empresas listadas na B3.
    Sua tarefa é buscar e sintetizar as notícias mais relevantes sobre a empresa analisada, focando em:

    ## OBJETIVOS DA ANÁLISE
    1. Identificar eventos significativos recentes que possam impactar a empresa
    2. Detectar mudanças estratégicas, aquisições, parcerias ou novos projetos
    3. Avaliar a percepção do mercado e da mídia sobre a empresa
    4. Monitorar riscos e oportunidades mencionados nas notícias
    5. Acompanhar declarações importantes da administração

    ## SUA ANÁLISE
    - Resuma cada notícia lida em poucas frases
    - Ao final, você deve fornecer uma conclusão objetiva em 3-5 frases sobre o sentimento geral das notícias e o impacto potencial no curto e médio prazo.

    ## DIRETRIZES IMPORTANTES
    - Mantenha objetividade na análise
    - Destaque fatos concretos, não especulações
    - Indique claramente a temporalidade das notícias
    - Foque em conteúdo relevante para investidores

    ## FORMATO FINAL (IMPORTANTE)
    Você deve estruturar a sua resposta em um JSON com a seguinte estrutura:
    {{
        "content": "Conteúdo markdown inteiro da sua análise",
        "sentiment": "Seu sentimento sobre a análise, você deve escolher entre 'BULLISH', 'BEARISH', 'NEUTRAL'",
        "confidence": "um valor entre 0 e 100, que representa sua confiança na análise",
    }}

    ---

    Dado o contexto, analise as notícias abaixo.
    Se a lista estiver vazia ou se as notícias não forem condinzentes com a empresa e o contexto, você deve retornar um content vazio, sentiment NEUTRAL, com confidence 0.
    {news}
    """

    try:
        agent = Agent(
            system_message=prompt,
            model=get_model(temperature=0.3),
            response_model=BaseAgentOutput,
            retries=3,
        )
        response = agent.run('Faça uma análise das notícias')
        return response.content
    except Exception as e:
        print(f'Erro ao gerar análise.: {e}')
        return BaseAgentOutput(content='Erro ao gerar análise.', sentiment='NEUTRAL', confidence=0)
