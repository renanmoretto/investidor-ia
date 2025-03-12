import time
from typing import TypedDict

import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from src.agents.base import BaseAgentOutput

from src.llm import ask


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


def analyse(ticker: str, company_name: str) -> BaseAgentOutput:
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

    ## ESTRUTURA DO SEU RESUMO
    Organize sua resposta em formato markdown seguindo esta estrutura:

    ### 1. PRINCIPAIS MANCHETES
    - Liste as 3-5 notícias mais impactantes encontradas
    - Inclua a data e fonte de cada notícia

    ### 2. EVENTOS CORPORATIVOS
    - Mudanças na administração
    - Fusões, aquisições ou desinvestimentos
    - Novos projetos ou investimentos significativos

    ### 3. DESEMPENHO E MERCADO
    - Notícias sobre resultados financeiros
    - Análises de mercado e recomendações de analistas
    - Mudanças no setor que afetam a empresa

    ### 4. RISCOS E CONTROVÉRSIAS
    - Processos judiciais relevantes
    - Investigações ou denúncias
    - Riscos regulatórios ou setoriais

    ### 5. CONCLUSÃO
    - Avaliação do sentimento geral das notícias
    - Impacto potencial no curto e médio prazo

    ## DIRETRIZES IMPORTANTES
    - Priorize fontes confiáveis e especializadas
    - Mantenha objetividade na análise
    - Destaque fatos concretos, não especulações
    - Indique claramente a temporalidade das notícias
    - Foque em conteúdo relevante para investidores

    ## FORMATO FINAL (IMPORTANTE)
    Você deve estruturar a sua resposta em um JSON com a seguinte estrutura:
    {{
        'content': 'Conteúdo markdown inteiro da sua análise',
        'sentiment': 'Seu sentimento sobre a análise, você deve escolher entre "BULLISH", "BEARISH", "NEUTRAL"',
        'confidence': 'um valor entre 0 e 100, que representa sua confiança na análise',
    }}

    Dado o contexto, analise as notícias abaixo.
    Se a lista estiver vazia ou se as notícias não forem condinzentes com a empresa e o contexto, você deve retornar um content vazio, sentiment NEUTRAL, com confidence 0.
    {news}
    """

    try:
        response = ask(
            message=prompt,
            model='gemini-1.5-flash-8b',
            temperature=0.3,
            model_output=BaseAgentOutput,
            retries=3,
        )
        return response
    except Exception as e:
        print(f'Erro ao gerar análise.: {e}')
        return BaseAgentOutput(content='Erro ao gerar análise.', sentiment='NEUTRAL', confidence=0)
