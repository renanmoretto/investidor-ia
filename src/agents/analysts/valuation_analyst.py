from src.llm import ask
from src.agents._base import BaseAgentOutput


def analyze(
    ticker: str,
    company_name: str,
    segment: str,
    current_price: float,
    current_multiples: dict,
    historical_multiples: dict,
    sector_multiples_mean: dict,
    sector_multiples_median: dict,
    market_multiples_median: dict,
) -> str:
    prompt = f"""
    Você é um analista especializado em valuation relativo de empresas. Sua tarefa é analisar se a empresa está cara ou barata em relação ao seu setor, mercado e seu próprio histórico, utilizando exclusivamente múltiplos e indicadores comparativos.

    ## EMPRESA ANALISADA
    Ticker: {ticker}
    Nome: {company_name}
    Setor: {segment}
    Preço Atual: {current_price}

    ## DADOS DISPONÍVEIS
    ### Múltiplos Atuais da Empresa
    {current_multiples}

    ### Múltiplos Históricos da Empresa (5 anos)
    {historical_multiples}

    ### Múltiplos do Setor (média) (pode ter distorções)
    {sector_multiples_mean}

    ### Múltiplos do Setor (mediana)
    {sector_multiples_median}

    ### Múltiplos do Mercado (mediana)
    {market_multiples_median}

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

    4. **Análise de Múltiplos Específicos**:
    - P/L (Preço/Lucro): Avalie se está caro ou barato em termos de lucros
    - P/VP (Preço/Valor Patrimonial): Avalie em termos de patrimônio
    - EV/EBITDA: Avalie em termos de geração de caixa operacional
    - P/FCF (Preço/Fluxo de Caixa Livre): Avalie em termos de geração de caixa livre
    - Dividend Yield: Compare com alternativas de renda fixa e média histórica

    ## DIRETRIZES IMPORTANTES
    - Foque exclusivamente em múltiplos e indicadores objetivos
    - Evite projeções futuras complexas ou modelos de desconto
    - Considere o contexto do setor ao fazer comparações
    - Identifique se há justificativas para prêmios ou descontos
    - Seja objetivo e imparcial na sua análise
    - Não faça recomendações diretas de compra/venda

    ## FORMATO DA SUA RESPOSTA
    Estruture sua análise em markdown seguindo este formato:

    ### ANÁLISE DE VALUATION RELATIVO

    #### Comparação com o Setor
    - [Análise detalhada dos principais múltiplos vs. setor]
    - [Prêmio/desconto percentual para cada múltiplo]
    - [Justificativas para eventuais diferenças]

    #### Comparação Histórica
    - [Análise dos múltiplos atuais vs. média histórica da empresa]
    - [Identificação de tendências nos múltiplos ao longo do tempo]
    - [Contexto para mudanças significativas]

    #### Múltiplos-Chave
    - **P/L**: [Análise do P/L atual vs. histórico e setor]
    - **P/VP**: [Análise do P/VP atual vs. histórico e setor]
    - **EV/EBITDA**: [Análise do EV/EBITDA atual vs. histórico e setor]
    - **Dividend Yield**: [Análise do yield atual vs. histórico e alternativas]

    #### Indicadores de Valor Relativo
    - [Ranking da empresa dentro do setor para cada múltiplo]
    - [Identificação de múltiplos onde a empresa se destaca positiva ou negativamente]
    - [Análise de correlação entre desempenho e múltiplos]

    #### CONCLUSÃO
    Uma síntese objetiva em 3-5 frases sobre se a empresa está cara, barata ou justamente precificada em relação ao setor, seu histórico e o mercado em geral.

    ## FORMATO FINAL (IMPORTANTE)
    Você deve estruturar a sua resposta em um JSON com a seguinte estrutura:
    {{
        'content': 'Conteúdo markdown inteiro da sua análise',
        'sentiment': 'Seu sentimento sobre a análise, você deve escolher entre "BULLISH", "BEARISH", "NEUTRAL"',
        'confidence': 'um valor entre 0 e 100, que representa sua confiança na análise',
    }}
    """

    response = ask(
        message=prompt,
        model='gemini-2.0-flash',
        temperature=0.3,
        model_output=BaseAgentOutput,
    )
    return response
