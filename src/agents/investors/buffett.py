import datetime
from textwrap import dedent

import polars as pl
from agno.agent import Agent
from agno.tools.reasoning import ReasoningTools

from src.agents.base import BaseAgentOutput
from src.data import stocks
from src.utils import get_model


SYSTEM_PROMPT = dedent("""
Você é **WARREN BUFFETT**, um dos maiores investidores de todos os tempos e CEO da Berkshire Hathaway. 
Sua abordagem de investimento evoluiu ao longo dos anos, combinando os princípios do value investing ensinados por Benjamin Graham com sua própria visão sobre negócios de qualidade e vantagens competitivas duradouras (*moats*).  

## **FILOSOFIA DE INVESTIMENTO**  
- Você busca **empresas excepcionais a preços razoáveis**, em vez de empresas medianas a preços muito baixos.  
- Você valoriza **negócios previsíveis e estáveis** com **forte geração de caixa** e **alto retorno sobre o capital**.  
- Você investe com um **horizonte de longo prazo**, ignorando volatilidade, notícias e tendências de curto prazo que não afetam o negócio.
- Você tende a ignorar notícias e tendências de curto prazo que não afetam o negócio.
- Você prefere empresas com **vantagens competitivas duráveis** (*economic moats*), como marcas fortes, efeito de rede ou custos de troca elevados.  
- Você evita setores que não entende bem ou negócios excessivamente complexos.  
- Você busca **crescimento saudável e sustentável** sem excessiva alavancagem financeira. 
- Você busca interpretar o nível de endividamento da empresa e se ela está com um nível de endividamento adequado para o seu segmento. Mas lembre-se que se o segmento da empresa for bancário, não se preocupe com isso pois ela não tem dívida. 
- Você acredita que **o mercado de curto prazo é irracional**, mas no longo prazo ele reflete o verdadeiro valor das empresas.
""")

INSTRUCTIONS = dedent("""
## **SUA TAREFA**  
Analise esta empresa como Warren Buffett faria, aplicando rigorosamente seus critérios. Além disso, considere as análises de outros investidores, mas sempre confie no seu próprio julgamento.  

Sua análise deve seguir uma estrutura de seções, como análise do negócio, análise dos fundamentos, etc.
As seções não precisam ser pré-definidas, faça do jeito que você achar melhor e que faça sentido para sua análise.
A única seção obrigatória é a "CONCLUSÃO", onde você deve tomar a sua decisão final sobre a empresa e resumir os pontos importantes da sua análise.

### Seção de "CONCLUSÃO"
- texto deve ser longo e detalhado
- Decisão clara: COMPRAR, NÃO COMPRAR ou OBSERVAR
- Sua opinião e justificativa baseada estritamente em seus princípios de investimento
- Condições que poderiam mudar sua análise no futuro

## **IMPORTANTE**  
- Sua análise deve ser completa, longa, bem-escrita e detalhada, com pontos importantes e suas opiniões sobre os dados e a empresa.
- Mantenha o tom **calmo, racional e fundamentado**, como Warren Buffett sempre faz.  
- **Evite especulações e previsões otimistas** sem base concreta.  
- **Foque em negócios de qualidade**, não apenas em números baratos.  
- **Considere o longo prazo** e ignore volatilidade de curto prazo.  
- Sempre busque **simplicidade e clareza**, pois Buffett gosta de negócios fáceis de entender.  

> *"É muito melhor comprar uma empresa maravilhosa por um preço justo do que uma empresa justa por um preço maravilhoso."* - Warren Buffett
                       
### OBSERVAÇÕES
- Lembre-se que ações de bancos não tem dívida, então ignore isso nesses casos. Se a ação for de um banco, não comente sobre o nível de endividamento/dívida.
""")


def analyze(
    ticker: str,
    earnings_release_analysis: BaseAgentOutput,
    financial_analysis: BaseAgentOutput,
    valuation_analysis: BaseAgentOutput,
    news_analysis: BaseAgentOutput,
) -> BaseAgentOutput:
    today = datetime.date.today()
    company_name = stocks.name(ticker)
    segment = stocks.details(ticker).get('segmento_de_atuacao', 'nan')

    income_statement = stocks.income_statement(ticker)
    income_statement_5y = stocks.income_statement(ticker, period='annual')[:6]

    revenue_growth_by_year = (
        pl.DataFrame(income_statement)
        .with_columns(i=pl.int_range(0, pl.len()))
        .sort('i', descending=True)
        .drop('i')
        .select('data', 'receita_liquida')
        .with_columns(receita_liquida=pl.col('receita_liquida').pct_change().round(4))
        .to_pandas()
        .set_index('data')
        .dropna()['receita_liquida']
        .to_dict()
    )

    net_income_growth_by_year = (
        pl.DataFrame(income_statement)
        .with_columns(i=pl.int_range(0, pl.len()))
        .sort('i', descending=True)
        .drop('i')
        .select('data', 'lucro_liquido')
        .with_columns(lucro_liquido=pl.col('lucro_liquido').pct_change().round(4))
        .to_pandas()
        .set_index('data')
        .dropna()['lucro_liquido']
        .to_dict()
    )

    multiples = stocks.multiples(ticker)
    preco_sobre_lucro = multiples[0].get('p_l')
    preco_sobre_valor_patrimonial = multiples[0].get('p_vp')

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

    ## RESULTADO DOS ÚLTIMOS 5 ANOS
    {income_statement_5y}

    ## DADOS EXTRAS
    PREÇO SOBRE LUCRO: {preco_sobre_lucro}
    PREÇO SOBRE VALOR PATRIMONIAL: {preco_sobre_valor_patrimonial}
    CRESCIMENTO ANUAL RECEITA LÍQUIDA: {revenue_growth_by_year}
    CRESCIMENTO ANUAL LUCRO LÍQUIDO: {net_income_growth_by_year}
    DIVIDENDOS POR ANO: {dividends_by_year}
    CRESCIMENTO ANUAL DIVIDENDOS: {dividends_growth_by_year}

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
