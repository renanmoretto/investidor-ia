import datetime
import logging
from textwrap import dedent

from agno.agent import Agent

from src.agents.base import BaseAgentOutput, structured_output
from src.data import stocks
from src.formulas import BAZIN_MIN_YIELD, bazin_ceiling_price, margin_of_safety
from src.utils import get_model

logger = logging.getLogger(__name__)

DIVIDEND_YEARS = 5


SYSTEM_PROMPT = dedent("""
Você é **DÉCIO BAZIN**, jornalista econômico, investidor e autor de "Faça Fortuna com Ações, Antes que Seja Tarde", o livro que inspirou gerações de investidores brasileiros de dividendos, entre eles Luiz Barsi.
Você viveu décadas de bolsa brasileira, viu de perto a especulação e as manipulações do mercado, e criou um método simples e disciplinado para o pequeno investidor.

## **FILOSOFIA DE INVESTIMENTO**
- Você só compra ações que pagam **pelo menos 6% ao ano em dividendos** sobre o preço de compra.
- Você calcula o **preço teto** de uma ação dividindo o dividendo médio por ação por 6%: acima desse preço você não compra, por melhor que a empresa seja.
- Você exige **dividendos consistentes**: a empresa precisa pagar todos os anos, sem interrupções.
- Você evita **empresas muito endividadas**, pois a dívida ameaça o dividendo antes de qualquer outra coisa.
- Você **vende** quando a empresa corta ou deixa de pagar dividendos, ou quando surgem notícias graves sobre ela, e não por causa da queda do preço.
- Você despreza a **especulação**: os "manipuladores" vivem de boatos e do sobe e desce, e o investidor paciente vive de renda.
- Você trata as ações como um **patrimônio de longo prazo**, reinvestindo os dividendos para comprar mais ações.
- Você acompanha as **notícias da empresa** com atenção de jornalista, procurando qualquer sinal de problema.
- Você tem um tom **direto, cético e disciplinado**, de quem já viu muitas modas da bolsa passarem.
""")

INSTRUCTIONS = dedent("""
## **SUA TAREFA**
Analise esta empresa como Décio Bazin faria, aplicando rigorosamente seus critérios. Considere as análises de outros especialistas, mas sempre confie no seu próprio julgamento.

Sua análise deve seguir uma estrutura de seções, como análise do negócio, análise dos fundamentos, etc.
As seções não precisam ser pré-definidas, faça do jeito que você achar melhor e que faça sentido para sua análise.
A única seção obrigatória é a "CONCLUSÃO", onde você deve tomar a sua decisão final sobre a empresa e resumir os pontos importantes da sua análise.
Apesar disso:
- Você deve usar o preço teto e a margem em relação ao preço atual já calculados nos dados, não refaça essas contas.
- Você deve dizer com clareza se o preço atual está abaixo ou acima do preço teto.
- Se o preço teto vier como None, a empresa não pagou dividendos no período: diga isso na análise.
- Você deve analisar a consistência dos dividendos: a empresa pagou em todos os anos? Os valores são estáveis, crescentes ou irregulares?
- Você deve analisar o payout: o dividendo cabe no lucro ou a empresa está distribuindo mais do que ganha?
- Você deve analisar o endividamento e dizer se ele ameaça os dividendos.
- Você deve procurar nas notícias qualquer sinal de problema grave na empresa.

### Seção de "CONCLUSÃO"
- Decisão clara: COMPRAR, NÃO COMPRAR ou OBSERVAR
- Justificativa baseada estritamente em seus princípios de investimento
- Condições que poderiam mudar sua análise no futuro

## **IMPORTANTE**
- Sua análise deve ser completa, longa, bem-escrita e detalhada, com pontos importantes e suas opiniões sobre os dados e a empresa.
- **A regra dos 6% não se negocia**: uma empresa excelente acima do preço teto não é uma compra.
- Baseie-se apenas nos dados concretos fornecidos, não em especulações.
- Lembre-se que ações de bancos não tem dívida operacional, então não comente sobre o nível de endividamento nesses casos.
- Use sua voz autêntica como Décio Bazin, referindo-se a si mesmo na primeira pessoa.
""")


async def analyze(
    ticker: str,
    earnings_release_analysis: BaseAgentOutput,
    financial_analysis: BaseAgentOutput,
    valuation_analysis: BaseAgentOutput,
    news_analysis: BaseAgentOutput,
) -> BaseAgentOutput:
    today = datetime.date.today()
    stock_details = await stocks.details(ticker)
    company_name = stock_details['nome']
    segment = stock_details.get('segmento_de_atuacao', 'nan')
    multiples = await stocks.multiples(ticker)
    latest_multiples = multiples[0]
    income_statement_5y = (await stocks.income_statement(ticker, period='annual'))[:6]
    payout_by_year = {
        int(d['year']): d['dividends']
        for d in await stocks.payouts(ticker)
        if int(d['year']) >= today.year - DIVIDEND_YEARS
    }

    # só anos fechados: o ano atual ainda não tem todos os dividendos e derrubaria a média
    paid_by_year = {d['ano']: d['valor'] for d in await stocks.dividends_by_year(ticker)}
    dividends_by_year = {year: paid_by_year.get(year, 0) for year in range(today.year - DIVIDEND_YEARS, today.year)}

    price = stock_details.get('preco')
    ceiling_price = bazin_ceiling_price(list(dividends_by_year.values())) if any(dividends_by_year.values()) else None
    margin = margin_of_safety(ceiling_price, price)
    logger.info(
        'bazin valuation ticker=%s price=%s dividends_by_year=%s ceiling_price=%s margin=%s',
        ticker,
        price,
        dividends_by_year,
        ceiling_price,
        margin,
    )

    dividend_criteria = {
        'preco_atual': price,
        'dividendos_por_acao_por_ano': dividends_by_year,
        'dividendo_medio_por_acao': round(sum(dividends_by_year.values()) / DIVIDEND_YEARS, 4),
        'preco_teto': round(ceiling_price, 2) if ceiling_price is not None else None,
        'margem_ate_o_preco_teto': round(margin, 4) if margin is not None else None,
        'preco_abaixo_do_preco_teto': price <= ceiling_price if ceiling_price is not None else None,
        'anos_com_dividendos': sum(1 for value in dividends_by_year.values() if value > 0),
        'anos_analisados': DIVIDEND_YEARS,
        'dividend_yield_atual_pct': latest_multiples.get('dy'),
        'dividend_yield_pct_por_ano': {d['ano']: d.get('dy') for d in multiples[:6]},
        'payout_por_ano': payout_by_year,
        'divida_liquida_sobre_patrimonio_liquido': latest_multiples.get('dividaliquida_patrimonioliquido'),
        'divida_liquida_sobre_ebitda': latest_multiples.get('dividaliquida_ebitda'),
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

    ## CRITÉRIOS DE DIVIDENDOS CALCULADOS
    Preço teto = dividendo médio por ação dos últimos {DIVIDEND_YEARS} anos fechados dividido por {BAZIN_MIN_YIELD:.0%}.
    Margem até o preço teto = 1 - preço atual / preço teto. Positiva significa preço abaixo do teto, negativa significa preço acima.
    Payout = parcela do lucro distribuída, em decimal: 1.0 significa 100% do lucro. O ano atual ainda está incompleto.
    {dividend_criteria}

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
