import asyncio
from typing import Any

from src.llm import ask
from src.agents.base import BaseAgentOutput


def analyze(
    ticker: str,
    company_name: str,
    segment: str,
    dre_quarter: Any,
    cash_flow_quarter: Any,
    balance_sheet_quarter: Any,
    stock_details: dict,
    cagr_5y_receita_liq: float,
    cagr_5y_lucro_liq: float,
    dividends_by_year: list,
    dividends_growth: float,
) -> str:
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

    ### Fluxo de Caixa
    {cash_flow_quarter}

    ### Múltiplos e Indicadores
    {stock_details}

    - cagr_5y_receita_liq: {cagr_5y_receita_liq}
    - cagr_5y_lucro_liq: {cagr_5y_lucro_liq}
    - dividends_by_year: {dividends_by_year}
    - dividends_growth: {dividends_growth}


    """

    try:
        response = ask(
            message=prompt,
            model='gemini-2.0-flash',
            temperature=0.3,
            model_output=BaseAgentOutput,
            retries=3,
        )
        return response
    except Exception as e:
        print(f'Erro ao gerar análise.: {e}')
        return BaseAgentOutput(content='Erro ao gerar análise.', sentiment='NEUTRAL', confidence=0)
