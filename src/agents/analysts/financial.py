import datetime

import polars as pl
from agno.agent import Agent

from src.utils import get_model
from src.agents.base import BaseAgentOutput
from src.data import stocks
from src.utils import calc_cagr


def analyze(ticker: str) -> str:
    today = datetime.date.today()
    year_start = today.year - 5
    year_end = today.year

    company_name = stocks.name(ticker)
    segment = stocks.details(ticker).get('segmento_de_atuacao', 'nan')
    dre_year = stocks.income_statement(ticker, year_start, year_end, 'year')
    dre_quarter = stocks.income_statement(ticker, year_start, year_end, 'quarter')
    balance_sheet_quarter = stocks.balance_sheet(ticker, year_start, year_end, 'quarter')
    cash_flow = stocks.cash_flow(ticker, year_start, year_end)
    stock_details = stocks.multiples(ticker)
    cagr_5y_receita_liq = calc_cagr(dre_year, 'receita_liquida', 5)
    cagr_5y_lucro_liq = calc_cagr(dre_year, 'lucro_liquido', 5)

    _dividends_by_year = stocks.dividends_by_year(ticker)
    if _dividends_by_year:
        dividends_growth_by_year = (
            pl.DataFrame(_dividends_by_year)
            .sort('ano')
            .with_columns(valor=pl.col('valor').pct_change().round(4))
            .drop_nulls()
            .to_dicts()
        )
        # tira dados do ano atual pra nao poluir a análise do AI
        dividends_by_year = [d for d in _dividends_by_year if d['ano'] < today.year]
        dividends_growth_by_year = [d for d in dividends_growth_by_year if d['ano'] < today.year]
    else:
        dividends_by_year = []
        dividends_growth_by_year = []

    prompt = f"""
    Você é um analista financeiro especializado em análise fundamentalista de demonstrações financeiras.
    Sua tarefa é analisar objetivamente os dados financeiros fornecidos e extrair conclusões imparciais sobre a qualidade dos números, saúde financeira e desempenho da empresa.

    ## SUA TAREFA
    Analise os dados financeiros fornecidos e produza uma interpretação concisa e objetiva. Sua análise deve:

    1. Identificar tendências significativas nos principais indicadores financeiros
    2. Destacar pontos fortes e fracos evidenciados pelos números
    3. Avaliar a saúde financeira geral da empresa
    4. Fornecer uma conclusão clara e imparcial baseada estritamente nos dados

    ## DIRETRIZES IMPORTANTES
    - Mantenha-se estritamente objetivo e imparcial
    - Baseie-se apenas nos dados fornecidos, sem especulações
    - Evite linguagem promocional ou excessivamente negativa
    - Priorize os indicadores mais relevantes para o tipo de negócio e setor
    - Seja conciso e direto, focando apenas nos pontos mais importantes
    - Não faça recomendações de investimento, apenas interprete os dados

    ## FORMATO DA SUA RESPOSTA
    Sua análise deve ser estruturada em markdown e conter no máximo 500 palavras, seguindo este formato:

    ### PONTOS PRINCIPAIS DA ANÁLISE FINANCEIRA

    #### Receita e Lucratividade
    - [Interpretação concisa sobre crescimento, margens e tendências]
    - [Interpretação sobre a qualidade dos dados financeiros, solidez e consistência da empresa]

    #### Crescimento
    - [Interpretação sobre o crescimento da empresa, incluindo crescimento de receita, lucro e dividendos]

    #### Remuneração ao acionista
    - [Interpretação sobre a remuneração ao acionista, incluindo dividendos e crescimento]

    #### Estrutura de Capital e Solvência
    - [Interpretação concisa sobre endividamento, liquidez e solidez financeira]

    #### Eficiência Operacional
    - [Interpretação concisa sobre uso de ativos, capital de giro e ciclos operacionais]
    - [Interpretação sobre a geração de caixa operacional e livre]

    #### CONCLUSÃO
    Uma síntese objetiva em 3-5 frases destacando os aspectos mais relevantes da análise e o que os números indicam sobre a situação atual da empresa.

    Lembre-se: sua análise deve ser factual, imparcial e baseada exclusivamente nos dados fornecidos.

    ## FORMATO FINAL (IMPORTANTE)
    Você deve estruturar a sua resposta em um JSON com a seguinte estrutura:
    {{
        "content": "Conteúdo markdown inteiro da sua análise",
        "sentiment": "Seu sentimento sobre a análise, você deve escolher entre 'BULLISH', 'BEARISH', 'NEUTRAL'",
        "confidence": "um valor entre 0 e 100, que representa sua confiança na análise",
    }}

    ---

    Dado o contexto, analise os dados financeiros fornecidos.
    Ticker: {ticker}
    Nome: {company_name}
    Setor: {segment}

    ## DADOS FINANCEIROS
    ### Demonstração de Resultados (DRE)
    {dre_quarter}

    ### Balanço Patrimonial
    {balance_sheet_quarter}

    ### Fluxo de Caixa Anual
    {cash_flow}

    ### Múltiplos e Indicadores
    {stock_details}

    - cagr_5y_receita_liq: {cagr_5y_receita_liq}
    - cagr_5y_lucro_liq: {cagr_5y_lucro_liq}
    - dividends_by_year: {dividends_by_year}
    - dividends_growth_by_year: {dividends_growth_by_year}


    """

    try:
        agent = Agent(
            system_message=prompt,
            model=get_model(temperature=0.3),
            response_model=BaseAgentOutput,
            retries=3,
        )
        response = agent.run('Faça uma análise da empresa')
        return response.content
    except Exception as e:
        print(f'Erro ao gerar análise.: {e}')
        return BaseAgentOutput(content='Erro ao gerar análise.', sentiment='NEUTRAL', confidence=0)
