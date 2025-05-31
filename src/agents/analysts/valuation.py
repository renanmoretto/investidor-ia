import polars as pl
from agno.agent import Agent

from src.utils import get_model
from src.agents.base import BaseAgentOutput
from src.data import stocks


def analyze(ticker: str) -> str:
    details = stocks.details(ticker)
    _screener = stocks.screener()
    screener = (
        pl.DataFrame(_screener)
        .with_columns(stock=pl.col('ticker').str.slice(0, 4))
        .sort('stock', 'liquidezmediadiaria')  # pega apenas o ticker que tem mais liquidez
        .unique('stock', keep='last')
        .filter(pl.col('price') > 0, pl.col('liquidezmediadiaria') > 0)
    )

    company_name = details['nome']
    segment = details.get('segmento_de_atuacao', 'nan')
    current_price = details.get('preco', float('nan'))
    five_years_historical_multiples = stocks.multiples(ticker)[:5]
    sector_multiples_mean = screener.filter(pl.col('segmentname') == segment).mean()
    sector_multiples_median = screener.filter(pl.col('segmentname') == segment).median()
    total_market_multiples_median = screener.median()

    prompt = f"""
    Você é um analista especializado em valuation relativo de empresas. Sua tarefa é analisar se a empresa está cara ou barata em relação ao seu setor, mercado e seu próprio histórico, utilizando exclusivamente múltiplos e indicadores comparativos.

    ## SUA TAREFA
    Analisar se a empresa está cara ou barata utilizando exclusivamente múltiplos comparativos:

    1. **Comparação com o Setor**:
    - Compare cada múltiplo da empresa com a média e mediana do setor
    - Calcule o prêmio ou desconto percentual em relação ao setor
    - Identifique se o prêmio ou desconto é justificável com base nos fundamentos

    2. **Comparação Histórica**:
    - Compare os múltiplos atuais com a média histórica da própria empresa
    - Identifique se a empresa está negociando acima ou abaixo de sua média histórica
    - Analise se houve mudanças fundamentais que justifiquem desvios da média histórica

    3. **Comparação com o Mercado Geral**:
    - Compare os múltiplos da empresa com o mercado como um todo
    - Avalie se o prêmio ou desconto em relação ao mercado é justificável

    4. **Análise de Múltiplos Específicos de acordo com cada setor e crescimento da empresa**:
        - Para empresas de alto crescimento (growth), foque em múltiplos como EV/Sales, EV/EBITDA, P/Sales e métricas de crescimento
        - Para empresas maduras e estáveis, priorize múltiplos como P/L, P/VP, DY e métricas de rentabilidade
        - Para empresas cíclicas, considere múltiplos ao longo do ciclo econômico
        - Para empresas de capital intensivo, dê atenção especial ao EV/EBITDA, ROIC, etc
        - Leve em consideração o setor da empresa para interpretar os múltiplos, setores mais especulativos/inovadores podem ter múltiplos maiores

    ## DIRETRIZES IMPORTANTES
    - Foque exclusivamente em múltiplos e indicadores objetivos
    - Evite projeções futuras complexas ou modelos de desconto
    - Considere o contexto do setor ao fazer comparações
    - Identifique se há justificativas para prêmios ou descontos
    - Seja objetivo e imparcial na sua análise
    - Não faça recomendações diretas de compra/venda

    ## FORMATO DA SUA RESPOSTA
    Estruture sua análise em markdown seguindo este formato:

    Sua análise deve seguir uma estrutura de seções, como análise dos múltiplos, análise dos indicadores, comparações, etc.
    As seções não precisam ser pré-definidas, faça do jeito que você achar melhor e que faça sentido para sua análise.
    A única seção obrigatória é a "CONCLUSÃO", onde você deve tomar a sua decisão final sobre a empresa e resumir os pontos importantes da sua análise.

    ### CONCLUSÃO
    Uma síntese objetiva em 3-5 frases sobre se a empresa está cara, barata ou justamente precificada em relação ao setor, seu histórico e o mercado em geral.

    ## FORMATO FINAL (IMPORTANTE)
    Você deve estruturar a sua resposta em um JSON com a seguinte estrutura:
    {{
        "content": "Conteúdo markdown inteiro da sua análise",
        "sentiment": "Seu sentimento sobre a análise, você deve escolher entre 'BULLISH', 'BEARISH', 'NEUTRAL'",
        "confidence": "um valor entre 0 e 100, que representa sua confiança na análise",
    }}

    ----

    Dado o contexto, analise a empresa abaixo.
    Ticker: {ticker}
    Nome: {company_name}
    Setor: {segment}
    Preço Atual: {current_price}

    ### Múltiplos Históricos da Empresa (5 anos)
    {five_years_historical_multiples}

    ### Múltiplos do Setor (média) (pode ter distorções)
    {sector_multiples_mean}

    ### Múltiplos do Setor (mediana)
    {sector_multiples_median}

    ### Múltiplos do Mercado (mediana)
    {total_market_multiples_median}

    """

    try:
        agent = Agent(
            system_message=prompt,
            model=get_model(temperature=0.3),
            response_model=BaseAgentOutput,
            retries=3,
        )
        response = agent.run('Faça uma análise do valuation')
        return response.content
    except Exception as e:
        print(f'Erro ao gerar análise.: {e}')
        return BaseAgentOutput(content='Erro ao gerar análise.', sentiment='NEUTRAL', confidence=0)
