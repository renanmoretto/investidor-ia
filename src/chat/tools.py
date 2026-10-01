import json
import logging

from pydantic import BaseModel, ValidationError

from src.chat.charts import build_chart_spec
from src.data import stocks

logger = logging.getLogger(__name__)


def detalhes(ticker: str) -> str:
    """
    Obtém os detalhes da ação.

    Args:
        ticker (str): O ticker para obter os detalhes.

    Returns:
        str: um JSON contendo os detalhes da ação.
        Exemplo (para PETR4):
            {
                'nome': 'PETROLEO BRASILEIRO S.A. PETROBRAS',
                'cnpj': '33.000.167/0001-01',
                'site': 'http://www.petrobras.com.br',
                'preco': 37.42,
                'patrimonio_liquido': 367514000000.0,
                'ativos': 1124797000000.0,
                'ativo_circulante': 135212000000.0,
                'divida_bruta': 373467000000.0,
                'disponibilidade': 46651000000.0,
                'divida_liquida': 326816000000.0,
                'valor_de_mercado': 509832636030.0,
                'valor_de_firma': 836648636030.0,
                'numero_de_acoes': 12888732761.0,
                'segmento_listagem': 'Nível 2',
                'free_float': 0.6125,
                'setor_de_atuacao': 'Petróleo. Gás e Biocombustíveis',
                'subsetor_de_atuacao': 'Petróleo. Gás e Biocombustíveis',
                'segmento_de_atuacao': 'Exploração. Refino e Distribuição'
            }
    """
    return json.dumps(stocks.details(ticker))


def multiplos(ticker: str, limit: int = 10) -> str:
    """
    Obtém o histórico anual de multiplos da ação.

    Args:
        ticker (str): O ticker para obter os multiplos.
        limit (int): O número máximo de anos a serem retornados. Default é 10 (últimos 10 anos).

    Returns:
        str: um JSON contendo o histórico anual de multiplos da ação.
        Exemplo (para PETR4):
            [
                {
                    'ano': 2025,
                    'dy': 21.1949,
                    'p_l': 13.1753,
                    'p_vp': 1.3123,
                    'p_ebita': 2.3615,
                    'p_ebit': 3.5153,
                    'p_sr': 0.9826,
                    'p_ativo': 0.4288,
                    'p_capitlgiro': -8.0928,
                    'p_ativocirculante': -0.4874,
                    'ev_ebitda': 4.0965,
                    'ev_ebit': 6.098,
                    'lpa': 2.8402,
                    'vpa': 28.5144,
                    'peg_Ratio': -0.18655978,
                    'dividaliquida_patrimonioliquido': 0.89,
                    'dividaliquida_ebitda': 1.6,
                    'dividaliquida_ebit': 2.38,
                    'patrimonio_ativo': 0.33,
                    'passivo_ativo': 0.67,
                    'liquidezcorrente': 0.69,
                    'margembruta': 50.21,
                    'margemebitda': 41.61,
                    'margemebit': 27.95,
                    'margemliquida': 7.46,
                    'roe': 9.96,
                    'roa': 3.25,
                    'roic': 16.12,
                    'giro_ativos': 0.44,
                    'receitas_cagr5': 10.18,
                    'lucros_cagr5': -1.82
                },
                ...
            ]
    """
    return json.dumps(stocks.multiples(ticker)[:limit])


def dados_financeiros(
    ticker: str,
    document: str,
    period: str = 'quarter',
    resultado_ltm: bool = False,
) -> str:
    """
    Obtém os dados financeiros da ação.
    Por exemplo:
    Se o usuario perguntar "Qual o lucro da Petrobras?" ou alguma informação sobre o resultado/DRE/balanço/fluxo de caixa da empresa,
    você deve chamar essa função com o ticker da empresa, no caso do exemplo, "PETR4" e o document 'resultados'.
    Na resposta, vai ter um JSON com todas as informações sobre o resultado/DRE/balanço/fluxo de caixa da empresa.

    Args:
        ticker (str): O ticker para obter os resultados.
        document (Literal['resultados', 'balanco', 'fluxo_caixa']): O documento para obter os resultados.
        period (Literal['quarter', 'annual']): O período para obter os resultados. 'quarter' são períodos trimestrais e 'annual' é anual. Default é 'quarter'.
        resultado_ltm (bool): Em caso de período anual para o documento 'resultados', se deve ter o resultado LTM (últimos 12 meses).
            PS: Caso o documento seja 'fluxo_caixa' ou 'balanco', o ltm será ignorado.
            Default é False.
    Returns:
        str: uma lista de JSON contendo os resultados da ação.
        Exemplo:
        [
            {
                'data': '4T2024',
                'receita_liquida': 121268000000.0,
                'custos': -63132000000.0,
                'lucro_bruto': 58136000000.0,
                'despesas/receitas_operacionais': -44967000000.0,
                'ebitda': 30652000000.0,
                'amortizacao/depreciacao': -17483000000.0,
                'ebit': 13169000000.0,
                'resultado_nao_operacional': nan,
                'resultado_financeiro': -34935000000.0,
                'impostos': 4804000000.0,
                'lucro_liquido': -16962000000.0,
                'lucro_atribuido_a_controladora': -17044000000.0,
                'lucro_atribuido_a_nao_controladores': 82000000.0,
                'capex': nan,
                'divida_bruta': 373467000000.0,
                'divida_liquida': nan,
                'roe': nan,
                'roic': nan,
                'margem_bruta': 0.4794,
                'margem_ebitda': 0.2528,
                'margem_liquida': -0.1399,
                'divida_liquida/ebitda': nan,
            },
            ...
        ]
    """
    if document == 'resultados':
        data = stocks.income_statement(ticker, period=period)
        if period == 'annual' and resultado_ltm:
            data = data[1:]
        return json.dumps(data)
    elif document == 'balanco':
        data = stocks.balance_sheet(ticker, period=period)
        return json.dumps(data)
    elif document == 'fluxo_caixa':
        data = stocks.cash_flow(ticker)
        return json.dumps(data)
    return "Erro: document deve ser 'resultados', 'balanco' ou 'fluxo_caixa'."


def dividendos(ticker: str, agrupar_por_ano: bool = False) -> str:
    """
    Obtém os dividendos da ação.
    Por exemplo:
    Se o usuario perguntar "Qual o dividendo da Petrobras?" ou alguma informação sobre os dividendos da empresa,
    você deve chamar essa função com o ticker da empresa, no caso do exemplo, "PETR4".
    Na resposta, vai ter um JSON com todas as informações sobre os dividendos da empresa.

    Args:
        ticker (str): O ticker para obter os dividendos.
        agrupar_por_ano (bool): Agrupa os dividendos por ano. Default é False.

    Returns:
        str: uma lista de JSON contendo os dividendos da ação.
    """
    if agrupar_por_ano:
        return json.dumps(stocks.dividends_by_year(ticker))
    return json.dumps(stocks.dividends(ticker))


class SerieGrafico(BaseModel):
    nome: str
    valores: list[float]


def criar_grafico(titulo: str, tipo: str, rotulos: list[str], series: list[SerieGrafico], unidade: str = '') -> str:
    """
    Exibe um gráfico para o usuário dentro do chat.
    Use sempre que uma evolução no tempo ou uma comparação ficar mais clara em um gráfico do que em texto,
    por exemplo: evolução do lucro, da receita, dos dividendos ou de múltiplos.
    Busque os dados com as outras funções antes de chamar esta. O gráfico aparece direto na tela do usuário,
    então não descreva o gráfico em formato de tabela nem diga que não consegue exibir gráficos.
    Use séries com a mesma unidade no mesmo gráfico. Para unidades diferentes, crie gráficos separados.

    Args:
        titulo (str): Título do gráfico. Exemplo: 'Lucro líquido da WEGE3'.
        tipo (str): 'line' para evolução no tempo ou 'bar' para comparar valores.
        rotulos (list[str]): Rótulos do eixo X em ordem cronológica. Exemplo: ['2021', '2022', '2023'].
        series (list[SerieGrafico]): Até 6 séries. Cada série tem 'nome' e 'valores',
            com um valor para cada rótulo. Exemplo: [{'nome': 'Lucro líquido', 'valores': [3.5, 4.2, 5.7]}].
        unidade (str): Unidade dos valores, exibida no eixo Y. Exemplo: 'R$ bilhões' ou '%'.

    Returns:
        str: confirmação de que o gráfico foi exibido, ou a descrição do erro.
    """
    try:
        spec = build_chart_spec(titulo, tipo, rotulos, series, unidade)
    except ValidationError as e:
        reason = '; '.join(error['msg'] for error in e.errors())
        logger.warning('chart rejected title=%s reason=%s', titulo, reason)
        return f'Erro ao criar o gráfico: {reason}'
    logger.info('chart created title=%s type=%s series=%d', titulo, spec['type'], len(spec['series']))
    return 'Gráfico exibido para o usuário.'


STOCK_TOOLS = [detalhes, multiplos, dados_financeiros, dividendos, criar_grafico]
