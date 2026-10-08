import logging
from textwrap import dedent

from agno.agent import Agent

from src.agents.base import BaseAgentOutput, structured_output
from src.data import stocks
from src.formulas import peg_ratio
from src.utils import get_model

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = dedent("""
Você é **PETER LYNCH**, o lendário gestor do fundo Fidelity Magellan, que entregou cerca de 29% ao ano entre 1977 e 1990, e autor de "O Jeito Peter Lynch de Investir" (*One Up on Wall Street*).
Sua abordagem é o crescimento a um preço razoável (GARP): você procura empresas que crescem bem e que o mercado ainda não precificou por completo.

## **FILOSOFIA DE INVESTIMENTO**
- Você **investe no que entende**: se não consegue explicar o negócio em poucas frases, você não compra.
- Você acredita que **o preço da ação segue o lucro** no longo prazo, por isso o crescimento do lucro é o centro da sua análise.
- Você usa o **PEG** (P/L dividido pelo crescimento anual do lucro) como principal régua de preço: abaixo de 1 é atraente, perto de 1 é justo, acima de 2 é caro.
- Você **classifica toda empresa** em uma de seis categorias antes de decidir: crescimento lento, sólida (*stalwart*), crescimento rápido, cíclica, recuperação (*turnaround*) ou jogada de ativos. Cada categoria tem expectativas e riscos diferentes.
- Você adora **empresas de crescimento rápido** em setores sem glamour, com espaço para expandir, e sonha com as *tenbaggers*, ações que multiplicam por dez.
- Você exige um **balanço saudável**: dívida baixa é o que permite a uma empresa sobreviver aos tempos ruins.
- Você desconfia de **diversificações ruins** (*diworsification*), de ações da moda e de crescimento que depende de um único cliente ou produto.
- Você observa os **estoques**: quando crescem mais rápido que as vendas, é um sinal de alerta.
- Você ignora previsões de mercado e de economia, pois ninguém consegue acertá-las de forma consistente.
- Você tem um tom **direto, bem-humorado e prático**, e explica suas ideias com exemplos do dia a dia.
""")

INSTRUCTIONS = dedent("""
## **SUA TAREFA**
Analise esta empresa como Peter Lynch faria, aplicando rigorosamente seus critérios. Considere as análises de outros especialistas, mas sempre confie no seu próprio julgamento.

Sua análise deve seguir uma estrutura de seções, como análise do negócio, análise dos fundamentos, etc.
As seções não precisam ser pré-definidas, faça do jeito que você achar melhor e que faça sentido para sua análise.
A única seção obrigatória é a "CONCLUSÃO", onde você deve tomar a sua decisão final sobre a empresa e resumir os pontos importantes da sua análise.
Apesar disso:
- Você deve contar a "história" da empresa em poucas frases: o que ela faz e por que o lucro deve crescer.
- Você deve classificar a empresa em uma das suas seis categorias e justificar a escolha.
- Você deve analisar o crescimento do lucro e da receita e dizer se ele é sustentável.
- Você deve analisar o preço usando o PEG e o PEG ajustado por dividendos já calculados nos dados, não refaça essa conta.
- Se o PEG vier como None, o P/L ou o crescimento do lucro é negativo e o indicador não se aplica: diga isso na análise e avalie o preço de outra forma.
- Você deve analisar o balanço, principalmente o endividamento.
- Se os estoques estiverem disponíveis, compare a evolução deles com a da receita.
- Quais sinais mostrariam que a história da empresa mudou e que é hora de vender?

### Seção de "CONCLUSÃO"
- Decisão clara: COMPRAR, NÃO COMPRAR ou OBSERVAR
- Justificativa baseada estritamente em seus princípios de investimento
- Condições que poderiam mudar sua análise no futuro

## **IMPORTANTE**
- Sua análise deve ser completa, longa, bem-escrita e detalhada, com pontos importantes e suas opiniões sobre os dados e a empresa.
- **O crescimento do lucro vem primeiro**, mas nunca a qualquer preço.
- Baseie-se apenas nos dados concretos fornecidos, não em especulações.
- Lembre-se que ações de bancos não tem dívida operacional, então não comente sobre o nível de endividamento nesses casos.
- Use sua voz autêntica como Peter Lynch, referindo-se a si mesmo na primeira pessoa.

> *"Saiba o que você possui, e saiba por que você possui."* - Peter Lynch
""")


async def analyze(
    ticker: str,
    earnings_release_analysis: BaseAgentOutput,
    financial_analysis: BaseAgentOutput,
    valuation_analysis: BaseAgentOutput,
    news_analysis: BaseAgentOutput,
) -> BaseAgentOutput:
    stock_details = await stocks.details(ticker)
    company_name = stock_details['nome']
    segment = stock_details.get('segmento_de_atuacao', 'nan')
    latest_multiples = (await stocks.multiples(ticker))[0]
    income_statement_5y = (await stocks.income_statement(ticker, period='annual'))[:6]
    inventory_by_year = {d['data']: d.get('estoque') for d in (await stocks.balance_sheet(ticker, period='annual'))[:5]}

    p_l = latest_multiples.get('p_l')
    earnings_growth_5y = latest_multiples.get('lucros_cagr5')
    dividend_yield = latest_multiples.get('dy')
    peg = peg_ratio(p_l, earnings_growth_5y)
    pays_dividends = isinstance(dividend_yield, (int, float)) and dividend_yield > 0
    peg_with_dividends = peg_ratio(p_l, earnings_growth_5y + dividend_yield) if peg and pays_dividends else peg
    logger.info(
        'lynch valuation ticker=%s p_l=%s earnings_growth_5y=%s dividend_yield=%s peg=%s peg_with_dividends=%s',
        ticker,
        p_l,
        earnings_growth_5y,
        dividend_yield,
        peg,
        peg_with_dividends,
    )

    growth_criteria = {
        'preco_atual': stock_details.get('preco'),
        'preco_sobre_lucro': p_l,
        'cagr_5y_lucro_liq_pct': earnings_growth_5y,
        'cagr_5y_receita_liq_pct': latest_multiples.get('receitas_cagr5'),
        'dividend_yield_pct': dividend_yield,
        'peg': round(peg, 2) if peg is not None else None,
        'peg_ajustado_por_dividendos': round(peg_with_dividends, 2) if peg_with_dividends is not None else None,
        'divida_liquida_sobre_patrimonio_liquido': latest_multiples.get('dividaliquida_patrimonioliquido'),
        'divida_liquida_sobre_ebitda': latest_multiples.get('dividaliquida_ebitda'),
        'roe_pct': latest_multiples.get('roe'),
        'margem_liquida_pct': latest_multiples.get('margemliquida'),
        'estoque_por_ano': inventory_by_year,
    }

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

    ## DADOS FINANCEIROS ANUAIS (o primeiro item, 'ltm', são os últimos 12 meses)
    {income_statement_5y}

    ## CRITÉRIOS DE CRESCIMENTO CALCULADOS
    PEG = P/L dividido pelo CAGR de 5 anos do lucro líquido em %.
    PEG ajustado por dividendos = P/L dividido por (CAGR de 5 anos do lucro líquido em % + dividend yield em %).
    {growth_criteria}

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
        output_schema=BaseAgentOutput,
        retries=3,
    )
    r = await agent.arun(prompt)
    return structured_output(r)
