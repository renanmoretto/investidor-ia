import requests

from src.llm import ask
from src.agents.base import BaseAgentOutput

from src.data import stocks
from src.data._sources import fundamentus


def _get_earnings_release(ticker: str) -> bytes:
    results_trimestrais = fundamentus.resultados_trimestrais(ticker)
    download_link = results_trimestrais[0]['download_link']
    if download_link is None:
        download_link = fundamentus.apresentacoes(ticker)[0]['download_link']

    if download_link is None:
        raise ValueError('Não foi possível encontrar o earnings release')

    r = requests.get(download_link)
    earnings_release_pdf_bytes = r.content
    return earnings_release_pdf_bytes


def analyze(ticker: str) -> BaseAgentOutput:
    company_name = stocks.name(ticker)
    try:
        release_pdf_bytes = _get_earnings_release(ticker)
    except Exception as e:
        print(f'Link de earnings release não encontrado: {e}')
        return BaseAgentOutput(content='Link de earnings release não encontrado', sentiment='NEUTRAL', confidence=0)

    prompt = f"""
    Você é um analista especializado em extrair e resumir informações relevantes de relatórios financeiros.
    Sua tarefa é analisar o PDF do último earnings release da empresa {company_name} - {ticker} e criar um resumo estruturado destacando os pontos mais importantes mencionados no documento.

    ## OBJETIVO
    Fornecer um resumo claro e objetivo dos principais pontos abordados no earnings release, sem adicionar informações externas ou criar dados não presentes no documento original.

    ## ESTRUTURA DO SEU RESUMO
    Organize sua resposta em formato markdown seguindo esta estrutura:

    ### 1. PRINCIPAIS DESTAQUES
    - Liste os 3-5 pontos mais importantes que a própria empresa destacou no relatório
    - Mantenha-se fiel ao que foi explicitamente mencionado no documento

    ### 2. MENSAGEM DA ADMINISTRAÇÃO
    - Resuma as principais declarações da liderança da empresa
    - Extraia citações relevantes sobre a visão da administração sobre os resultados
    - PS: essa seção é opcional, se não houver conteúdo para resumir, você pode simplesmente ignorar esta seção

    ### 3. DESENVOLVIMENTOS ESTRATÉGICOS
    - Iniciativas, parcerias ou mudanças estratégicas mencionadas
    - Novos produtos, serviços ou mercados destacados no relatório

    ### 4. PERSPECTIVAS FUTURAS
    - Resumo das expectativas e projeções mencionadas pela empresa
    - Planos futuros ou direcionamentos estratégicos comunicados

    ### 5. DESAFIOS E RISCOS
    - Obstáculos ou dificuldades explicitamente mencionados no relatório
    - Fatores de risco que a própria empresa destacou

    ### 6. CONCLUSÃO E OPINIÃO
    - Resuma as principais conclusões e opiniões sobre o relatório
    - Dê sua opinião sobre a empresa e seus resultados, escreva de forma simples e objetiva se o resultado foi positivo, negativo ou misto

    ## DIRETRIZES IMPORTANTES
    - Limite-se EXCLUSIVAMENTE ao conteúdo presente no documento
    - NÃO crie, calcule ou infira dados financeiros não explicitamente mencionados
    - Use as próprias palavras e terminologia da empresa sempre que possível
    - Priorize informações qualitativas e estratégicas sobre números específicos
    - Use bullet points para facilitar a leitura rápida

    ## FORMATO FINAL
    Seu conteúdo deve ser conciso (máximo de 800 palavras), focando apenas nos pontos mais relevantes mencionados no documento.
    (IMPORTANTE) Você deve estruturar a sua resposta em um JSON com a seguinte estrutura:
    {{
        "content": "Conteúdo markdown inteiro da sua análise",
        "sentiment": "Seu sentimento sobre a análise, você deve escolher entre 'BULLISH', 'BEARISH', 'NEUTRAL'",
        "confidence": "um valor entre 0 e 100, que representa sua confiança na análise",
    }}
    """

    try:
        response = ask(
            message=prompt,
            model='gemini-1.5-flash-8b',
            temperature=0.3,
            pdf_content=release_pdf_bytes,
            model_output=BaseAgentOutput,
            retries=3,
        )
        return response
    except Exception as e:
        print(f'Erro ao analisar o earnings release: {e}')
        return BaseAgentOutput(content='Erro ao analisar o earnings release', sentiment='NEUTRAL', confidence=0)
