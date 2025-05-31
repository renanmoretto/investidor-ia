import datetime
from textwrap import dedent

import polars as pl
from agno.agent import Agent
from agno.tools.reasoning import ReasoningTools

from src.agents.base import BaseAgentOutput
from src.data import stocks
from src.utils import calc_cagr, get_model


SYSTEM_PROMPT = dedent("""
Você é **LUIZ BARSI**, conhecido como o "Bilionário dos Dividendos" e o maior investidor pessoa física da bolsa brasileira. 
Sua estratégia de investimento é focada na construção de uma "carteira previdenciária" através de ações que pagam dividendos consistentes e crescentes ao longo do tempo.  

## **FILOSOFIA DE INVESTIMENTO**  
- Você busca **empresas sólidas** que atuam em setores perenes e essenciais da economia.  
- Você valoriza **empresas que pagam dividendos consistentes e crescentes**, criando uma renda passiva substancial.  
- Você investe com **horizonte de longo prazo**, ignorando volatilidades de curto prazo e focando na geração de renda.  
- Você prefere **setores regulados e previsíveis** como utilities (energia elétrica, saneamento), bancos e papel e celulose.  
- Você valoriza **empresas com baixo endividamento** e boa geração de caixa operacional.  
- Você evita empresas com alta volatilidade ou que dependem de ciclos econômicos específicos.  
- Você busca **preços razoáveis**, mas não se preocupa tanto com o "timing perfeito" de compra.  
- Você acredita que **reinvestir dividendos** é a chave para construir um patrimônio significativo.
""")

INSTRUCTIONS = dedent("""
## **SUA TAREFA**  
Analise esta empresa como Luiz Barsi faria, aplicando rigorosamente seus critérios. Considere as análises de outros especialistas, mas sempre confie no seu próprio julgamento baseado em sua filosofia de dividendos.  

Sua análise deve seguir uma estrutura de seções, como análise do negócio, análise dos fundamentos, etc.
As seções não precisam ser pré-definidas, faça do jeito que você achar melhor e que faça sentido para sua análise.
A única seção obrigatória é a "CONCLUSÃO", onde você deve tomar a sua decisão final sobre a empresa e resumir os pontos importantes da sua análise.
Apesar disso:
- Você deve analisar o histórico de dividendos da empresa, sua geração de caixa, seu payout e seu crescimento de dividendos.
- Você deve analisar a qualidade dos dividendos da empresa, se eles são consistentes e crescentes.
- Você deve analisar a saúde financeira da empresa, incluindo seu endividamento, margem de lucro, ROE e geração de caixa.
- Quais são os principais riscos para a continuidade dos dividendos?  
- Existem mudanças regulatórias ou setoriais que podem afetar a capacidade de pagamento?  
- A empresa pode manter sua posição competitiva no longo prazo?

### Seção de "CONCLUSÃO"
- Decisão clara: COMPRAR, NÃO COMPRAR ou OBSERVAR
- Justificativa baseada estritamente em seus princípios de investimento
- Condições que poderiam mudar sua análise no futuro

## **IMPORTANTE**
- Sua análise deve ser completa, longa, bem-escrita e detalhada, com pontos importantes e suas opiniões sobre os dados e a empresa.
- **Priorize a geração de renda passiva** sobre ganhos de capital.  
- **Considere o longo prazo** e ignore volatilidades temporárias.  
- Sempre busque **empresas que você entenda facilmente**, pois Barsi valoriza a simplicidade nos negócios.  

> *"O segredo é comprar ações de empresas sólidas, que pagam bons dividendos, e reinvestir esses dividendos. Com o tempo, você constrói uma renda passiva substancial."* - Luiz Barsi  
""")


def analyze(
    ticker: str,
    earnings_release_analysis: BaseAgentOutput,
    financial_analysis: BaseAgentOutput,
    valuation_analysis: BaseAgentOutput,
    news_analysis: BaseAgentOutput,
) -> BaseAgentOutput:
    today = datetime.date.today()
    year_start = today.year - 5
    year_end = today.year

    company_name = stocks.name(ticker)
    segment = stocks.details(ticker).get('segmento_de_atuacao', 'nan')
    multiples = stocks.multiples(ticker)
    dre_year = stocks.income_statement(ticker, year_start, year_end, 'year')
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

    preco_sobre_lucro = multiples[0].get('p_l')
    preco_sobre_valor_patrimonial = multiples[0].get('p_vp')
    dividend_yield = multiples[0].get('dy')
    try:
        dividend_yield_per_year = {d['ano']: d['dy'] for d in multiples}
    except Exception:
        dividend_yield_per_year = {}

    payouts = stocks.payouts(ticker)

    prompt = dedent(f"""
    Dado o contexto, analise a empresa abaixo.
    Nome: {company_name}
    Ticker: {ticker}
    Setor: {segment}

    ## OPINIÃO DO ANALISTA SOBRE O ÚLTIMO EARNINGS RELEASE
    Sentimento: {earnings_release_analysis.sentiment}
    Confiança: {earnings_release_analysis.confidence}
    Análise: {earnings_release_analysis.content}

    ## OPINIÃO DO ANALISTA SOBRE OS DADOS FINANCEIROS DA EMPRESA
    Sentimento: {financial_analysis.sentiment}
    Confiança: {financial_analysis.confidence}
    Análise: {financial_analysis.content}

    ## OPINIÃO DO ANALISTA SOBRE O VALUATION DA EMPRESA
    Sentimento: {valuation_analysis.sentiment}
    Confiança: {valuation_analysis.confidence}
    Análise: {valuation_analysis.content}

    ## OPINIÃO DO ANALISTA SOBRE AS NOTÍCIAS DA EMPRESA
    Sentimento: {news_analysis.sentiment}
    Confiança: {news_analysis.confidence}
    Análise: {news_analysis.content}

    ## DADOS FINANCEIROS DISPONÍVEIS
    {dre_year}

    ## DADOS EXTRAS
    PREÇO SOBRE LUCRO: {preco_sobre_lucro}
    PREÇO SOBRE VALOR PATRIMONIAL: {preco_sobre_valor_patrimonial}
    CAGR 5Y RECEITA LIQ: {cagr_5y_receita_liq}
    CAGR 5Y LUCRO LIQ: {cagr_5y_lucro_liq}
    CRES. DIVIDENDOS ANUAIS: {dividends_growth_by_year}
    DIVIDEND YIELD ATUAL: {dividend_yield}
    HISTÓRICO DE DIVIDENDOS: {dividends_by_year}
    HISTÓRICO DE DIVIDEND YIELD POR ANO: {dividend_yield_per_year}
    HISTÓRICO DE PAYOUTS (EM %): {payouts}

    ## FORMATO FINAL DA SUA RESPOSTA (**IMPORTANTE**)
    Você deve estruturar a sua resposta em um JSON com a seguinte estrutura:
    {{
        "content": "Conteúdo markdown inteiro da sua análise",
        "sentiment": "Seu sentimento sobre a análise, você deve escolher entre 'BULLISH', 'BEARISH', 'NEUTRAL'",
        "confidence": "um valor entre 0 e 100, que representa sua confiança na análise",
    }}
    """)

    agent = Agent(
        model=get_model(),
        system_message=SYSTEM_PROMPT,
        instructions=INSTRUCTIONS,
        tools=[ReasoningTools(think=True, analyze=True)],
        response_model=BaseAgentOutput,
        retries=3,
    )
    r = agent.run(prompt)
    return r.content
