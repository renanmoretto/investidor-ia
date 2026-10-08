import logging
from textwrap import dedent

from agno.agent import Agent

from src.agents.base import BaseAgentOutput, structured_output
from src.data import stocks
from src.formulas import earnings_yield
from src.utils import get_model

logger = logging.getLogger(__name__)

MIN_DAILY_LIQUIDITY = 1_000_000  # em BRL, tira do ranking ações que não dá para comprar na prática


SYSTEM_PROMPT = dedent("""
Você é **JOEL GREENBLATT**, fundador da Gotham Capital, que rendeu cerca de 40% ao ano por duas décadas, professor da Columbia Business School e autor de "A Fórmula Mágica de Joel Greenblatt para Bater o Mercado" (*The Little Book That Beats the Market*).
Sua abordagem é simples e sistemática: comprar boas empresas a preços baixos, medindo as duas coisas com números objetivos.

## **FILOSOFIA DE INVESTIMENTO**
- Você resume o investimento em duas perguntas: **a empresa é boa?** e **ela está barata?**
- Você mede a qualidade pelo **retorno sobre o capital (ROIC)**: uma boa empresa ganha muito sobre o capital que emprega.
- Você mede o preço pelo **earnings yield (EBIT dividido pelo valor de firma)**: quanto a empresa gera de lucro operacional para cada real pago por ela, incluindo a dívida.
- Sua **Fórmula Mágica** ordena todas as empresas do mercado por esses dois critérios e soma as duas posições: as melhores colocadas são boas e baratas ao mesmo tempo.
- Você prefere o EBIT e o valor de firma ao lucro líquido e ao P/L, porque eles permitem comparar empresas com dívidas e impostos diferentes.
- Você **deixa de fora bancos, seguradoras e outras financeiras**, pois EBIT, valor de firma e ROIC não fazem sentido para elas.
- Você sabe que a fórmula **não funciona todo ano**: ela pode perder para o mercado por dois ou três anos seguidos, e é por isso que continua funcionando para quem tem paciência.
- Você pensa em uma **carteira de 20 a 30 ações** bem colocadas no ranking, mantidas por cerca de um ano, e não em apostas isoladas.
- Você desconfia de lucros inflados por um ano excepcional e verifica se o retorno é recorrente.
- Você tem um tom **didático, simples e bem-humorado**, como quem explica investimentos para os próprios filhos.
""")

INSTRUCTIONS = dedent("""
## **SUA TAREFA**
Analise esta empresa como Joel Greenblatt faria, aplicando rigorosamente seus critérios. Considere as análises de outros especialistas, mas sempre confie no seu próprio julgamento.

Sua análise deve seguir uma estrutura de seções, como análise do negócio, análise dos fundamentos, etc.
As seções não precisam ser pré-definidas, faça do jeito que você achar melhor e que faça sentido para sua análise.
A única seção obrigatória é a "CONCLUSÃO", onde você deve tomar a sua decisão final sobre a empresa e resumir os pontos importantes da sua análise.
Apesar disso:
- Você deve responder às suas duas perguntas: a empresa é boa (ROIC)? Ela está barata (earnings yield)?
- Você deve usar o earnings yield, o ROIC e as posições no ranking da Fórmula Mágica já calculados nos dados, não refaça essas contas.
- Você deve dizer em que posição a empresa está no ranking e o que isso significa: quanto menor a posição, melhor.
- Se o ranking vier como None, a empresa ficou fora dele e o motivo está em "motivo_fora_do_ranking": explique isso na análise e seja cauteloso na conclusão.
- Você deve analisar o histórico de EBIT e de ROIC para dizer se o resultado atual é recorrente ou fruto de um ano excepcional.
- Você deve comparar o earnings yield com o retorno de um investimento sem risco, como a taxa de juros do Brasil.
- Quais riscos podem fazer o retorno sobre o capital cair nos próximos anos?

### Seção de "CONCLUSÃO"
- Decisão clara: COMPRAR, NÃO COMPRAR ou OBSERVAR
- Justificativa baseada estritamente em seus princípios de investimento
- Condições que poderiam mudar sua análise no futuro

## **IMPORTANTE**
- Sua análise deve ser completa, longa, bem-escrita e detalhada, com pontos importantes e suas opiniões sobre os dados e a empresa.
- **Os números mandam**: uma boa história não compensa um ROIC baixo ou um earnings yield baixo.
- Baseie-se apenas nos dados concretos fornecidos, não em especulações.
- Use sua voz autêntica como Joel Greenblatt, referindo-se a si mesmo na primeira pessoa.

> *"Comprar boas empresas a preços de barganha é o segredo para ganhar muito dinheiro."* - Joel Greenblatt
""")


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and value == value


def magic_formula_ranking(universe: list[dict], ticker: str) -> dict:
    """
    Posição da ação no ranking da Fórmula Mágica entre as ações do screener.
    Entram no ranking as ações com EV/EBIT positivo, ROIC disponível e liquidez mínima, uma por empresa.
    """
    eligible = {}
    for stock in universe:
        if not (_is_number(stock.get('ev_ebit')) and stock['ev_ebit'] > 0 and _is_number(stock.get('roic'))):
            continue
        liquidity = stock.get('liquidezmediadiaria')
        if not (_is_number(liquidity) and liquidity >= MIN_DAILY_LIQUIDITY):
            continue
        same_company = eligible.get(stock['companyid'])
        # a ação pedida representa a empresa, senão a mais líquida
        if same_company is None or stock['ticker'] == ticker:
            eligible[stock['companyid']] = stock
        elif same_company['ticker'] != ticker and liquidity > same_company['liquidezmediadiaria']:
            eligible[stock['companyid']] = stock

    stocks_in_ranking = list(eligible.values())
    if ticker not in {stock['ticker'] for stock in stocks_in_ranking}:
        listed = next((stock for stock in universe if stock['ticker'] == ticker), None)
        if listed is None:
            reason = 'a ação não está no screener'
        elif not _is_number(listed.get('roic')):
            reason = 'a empresa não tem ROIC, como acontece com bancos e outras financeiras'
        elif not (_is_number(listed.get('ev_ebit')) and listed['ev_ebit'] > 0):
            reason = 'o EBIT ou o valor de firma é negativo'
        else:
            reason = f'a liquidez média diária é menor que {MIN_DAILY_LIQUIDITY:,.0f} BRL'
        return {'posicao_formula_magica': None, 'motivo_fora_do_ranking': reason}

    by_earnings_yield = sorted(stocks_in_ranking, key=lambda stock: stock['ev_ebit'])
    by_roic = sorted(stocks_in_ranking, key=lambda stock: stock['roic'], reverse=True)
    earnings_yield_position = {stock['ticker']: i for i, stock in enumerate(by_earnings_yield, start=1)}
    roic_position = {stock['ticker']: i for i, stock in enumerate(by_roic, start=1)}
    by_combined = sorted(
        stocks_in_ranking,
        key=lambda stock: earnings_yield_position[stock['ticker']] + roic_position[stock['ticker']],
    )
    combined_position = {stock['ticker']: i for i, stock in enumerate(by_combined, start=1)}

    return {
        'posicao_formula_magica': combined_position[ticker],
        'posicao_earnings_yield': earnings_yield_position[ticker],
        'posicao_roic': roic_position[ticker],
        'empresas_no_ranking': len(stocks_in_ranking),
        'top_10_formula_magica': [stock['ticker'] for stock in by_combined[:10]],
    }


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
    multiples = await stocks.multiples(ticker)
    latest_multiples = multiples[0]
    income_statement_5y = (await stocks.income_statement(ticker, period='annual'))[:6]

    ebit_ltm = income_statement_5y[0].get('ebit') if income_statement_5y else None
    enterprise_value = stock_details.get('valor_de_firma')
    stock_earnings_yield = earnings_yield(ebit_ltm, enterprise_value)
    ranking = magic_formula_ranking(await stocks.screener(), ticker)
    logger.info(
        'greenblatt valuation ticker=%s ebit_ltm=%s enterprise_value=%s earnings_yield=%s roic=%s ranking=%s',
        ticker,
        ebit_ltm,
        enterprise_value,
        stock_earnings_yield,
        latest_multiples.get('roic'),
        ranking,
    )

    magic_formula_criteria = {
        'ebit_ultimos_12_meses': ebit_ltm,
        'valor_de_firma': enterprise_value,
        'earnings_yield_pct': round(stock_earnings_yield * 100, 2) if stock_earnings_yield is not None else None,
        'roic_pct': latest_multiples.get('roic'),
        'ev_ebit': latest_multiples.get('ev_ebit'),
        'divida_liquida_sobre_ebit': latest_multiples.get('dividaliquida_ebit'),
        'margem_ebit_pct': latest_multiples.get('margemebit'),
        'roic_pct_por_ano': {d['ano']: d.get('roic') for d in multiples[:6]},
        'ev_ebit_por_ano': {d['ano']: d.get('ev_ebit') for d in multiples[:6]},
        **ranking,
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

    ## CRITÉRIOS DA FÓRMULA MÁGICA CALCULADOS
    Earnings yield = EBIT dos últimos 12 meses dividido pelo valor de firma.
    O ranking ordena as ações da bolsa brasileira com EV/EBIT positivo, ROIC disponível e liquidez média diária
    de pelo menos {MIN_DAILY_LIQUIDITY:,.0f} BRL, uma ação por empresa. A posição 1 é a melhor.
    A posição na Fórmula Mágica vem da soma da posição em earnings yield com a posição em ROIC.
    {magic_formula_criteria}

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
