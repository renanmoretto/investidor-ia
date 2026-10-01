import asyncio
import logging
from typing import TypedDict

import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS
from ddgs.exceptions import DDGSException, RatelimitException, TimeoutException
from agno.agent import Agent

from src.utils import get_model
from src.agents.base import BaseAgentOutput
from src.data import stocks

logger = logging.getLogger(__name__)

SEARCH_RETRY_WAITS = [2, 5, 10]
ARTICLE_TIMEOUT = 15


class News(TypedDict):
    title: str
    url: str
    body: str
    content: str


async def _search(query: str) -> list[dict]:
    """Runs the search. Returns an empty list when DuckDuckGo stays unavailable, so the report continues without news."""
    for attempt, wait in enumerate([*SEARCH_RETRY_WAITS, None], start=1):
        try:
            # the DuckDuckGo client is sync only
            results = await asyncio.to_thread(DDGS().text, query, max_results=5, region='br-pt', timelimit='3m')
            logger.info('news search done attempt=%d results=%d', attempt, len(results))
            return results
        except (RatelimitException, TimeoutException) as e:
            if wait is None:
                logger.error('news search failed after %d attempts, continuing without news error=%s', attempt, e)
                return []
            logger.warning('news search attempt=%d failed, retry in %ds error=%s', attempt, wait, e)
            await asyncio.sleep(wait)
        except DDGSException as e:
            logger.error('news search failed, continuing without news error=%s', e)
            return []
    return []


async def _article_content(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=ARTICLE_TIMEOUT, follow_redirects=True) as client:
            r = await client.get(url)
        r.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning('news article download failed url=%s error=%s', url, e)
        return 'Conteúdo não encontrado'
    soup_content = BeautifulSoup(r.text, 'html.parser').find('div', class_='content-editor')
    return soup_content.text if soup_content else 'Conteúdo não encontrado'


async def _search_news_einvestidor(ticker: str, company_name: str) -> list[News]:
    results = await _search(
        f'notícias sobre a empresa {company_name} (ticker {ticker}) site:einvestidor.estadao.com.br'
    )

    news = []
    for result in results:
        url = result['href']
        if '/tag/' in url:
            continue
        news.append(
            {'title': result['title'], 'url': url, 'body': result['body'], 'content': await _article_content(url)}
        )
        await asyncio.sleep(1)

    logger.info('news collected ticker=%s count=%d', ticker, len(news))
    return news


async def analyze(ticker: str) -> BaseAgentOutput:
    company_name = await stocks.name(ticker)
    news = await _search_news_einvestidor(ticker, company_name)

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
            output_schema=BaseAgentOutput,
            retries=3,
        )
        response = await agent.arun('Faça uma análise das notícias')
        return response.content
    except Exception as e:
        print(f'Erro ao gerar análise.: {e}')
        return BaseAgentOutput(content='Erro ao gerar análise.', sentiment='NEUTRAL', confidence=0)
