import argparse

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from src.agents.analysts import (
    earnings_release,
    financial,
    news,
    technical,
    valuation,
)
from src.agents.investors import (
    graham,
    buffett,
    lynch,
    barsi,
)
from src.data import stocks


def investor_analyze(
    ticker: str,
    investor_name: str,
):
    ticker = ticker.upper()

    # verifica se o ticker existe
    stocks.details(ticker)

    # ai analysts
    print('Analisando earnings release...')
    earnings_release_analysis = earnings_release.analyze(ticker)

    print('Analisando dados financeiros...')
    financial_analysis = financial.analyze(ticker)

    print('Analisando valuation...')
    valuation_analysis = valuation.analyze(ticker)

    print('Analisando notícias...')
    news_analysis = news.analyze(ticker=ticker)

    # investor analysis
    print('Gerando resposta final...')
    if investor_name == 'buffett':
        investor_analysis = buffett.analyze(
            ticker=ticker,
            earnings_release_analysis=earnings_release_analysis,
            financial_analysis=financial_analysis,
            valuation_analysis=valuation_analysis,
            news_analysis=news_analysis,
        )

    elif investor_name == 'graham':
        investor_analysis = graham.analyze(
            ticker=ticker,
            earnings_release_analysis=earnings_release_analysis,
            financial_analysis=financial_analysis,
            valuation_analysis=valuation_analysis,
            news_analysis=news_analysis,
        )

    elif investor_name == 'lynch':
        raise NotImplementedError('Peter Lynch analysis not implemented yet')

    elif investor_name == 'barsi':
        investor_analysis = barsi.analyze(
            ticker=ticker,
            earnings_release_analysis=earnings_release_analysis,
            financial_analysis=financial_analysis,
            valuation_analysis=valuation_analysis,
            news_analysis=news_analysis,
        )

    else:
        raise ValueError(f'Investor {investor_name} not found')

    return {
        'analysts': {
            'earnings_release_analyst': earnings_release_analysis,
            'financial_analyst': financial_analysis,
            'valuation_analyst': valuation_analysis,
            'news_analyst': news_analysis,
        },
        'investor': investor_analysis,
    }


def print_result(analysis: dict, investor_name: str):
    console = Console()

    sentiment_color = {'BULLISH': 'green', 'BEARISH': 'red', 'NEUTRAL': 'yellow'}

    _table_data = [
        {
            'Análise': 'Release',
            'Sentimento': analysis['analysts']['earnings_release_analyst'].sentiment,
            'Confiança': f'{analysis["analysts"]["earnings_release_analyst"].confidence}%',
        },
        {
            'Análise': 'Financeira',
            'Sentimento': analysis['analysts']['financial_analyst'].sentiment,
            'Confiança': f'{analysis["analysts"]["financial_analyst"].confidence}%',
        },
        {
            'Análise': 'Valuation',
            'Sentimento': analysis['analysts']['valuation_analyst'].sentiment,
            'Confiança': f'{analysis["analysts"]["valuation_analyst"].confidence}%',
        },
        {
            'Análise': 'Notícias',
            'Sentimento': analysis['analysts']['news_analyst'].sentiment,
            'Confiança': f'{analysis["analysts"]["news_analyst"].confidence}%',
        },
    ]

    table = Table(title='Analistas')
    table.add_column('Análise')
    table.add_column('Sentimento', justify='center')
    table.add_column('Confiança', justify='center')

    for row in _table_data:
        sentiment = row['Sentimento']

        table.add_row(row['Análise'], f'[{sentiment_color[sentiment]}]{sentiment}[/]', row['Confiança'])

    console.print('')
    console.print('')
    console.print(table)
    console.print('')
    console.print('')
    # output investor analysis
    console.print(f'Análise de {investor_name.capitalize()}')
    console.print('Sentimento: ', style='bold', end='')
    console.print(analysis['investor'].sentiment, style=sentiment_color[analysis['investor'].sentiment])
    console.print('Confiança: ', style='bold', end='')
    console.print(f'{analysis["investor"].confidence}%')
    console.print(Markdown(analysis['investor'].content))
    console.print('')
    console.print('')
    # disclaimer
    console.print('Disclaimer:', style='bold red dim')
    console.print(
        'Este relatório foi gerado por um sistema de Inteligência Artificial e NÃO constitui recomendação de investimento.',
        style='dim',
    )
    console.print(
        'As análises apresentadas são meramente informativas e não devem ser utilizadas como única base para decisões de investimento.',
        style='dim',
    )
    console.print(
        'Os desenvolvedores e o sistema não se responsabilizam por eventuais perdas ou ganhos decorrentes do uso destas informações.',
        style='dim',
    )
    console.print(
        'Investimentos em renda variável envolvem riscos e podem resultar em perdas patrimoniais.', style='dim'
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ticker', type=str, help='Ticker da ação')
    parser.add_argument('--investor', type=str, help='Investidor')
    args = parser.parse_args()

    if args.ticker:
        ticker = args.ticker
    else:
        ticker = input('Ticker: ')

    if args.investor:
        investor_name = args.investor
    else:
        print('\nEscolha o investidor:')
        print('1 - Warren Buffett')
        print('2 - Benjamin Graham')
        print('3 - Peter Lynch')
        print('4 - Luiz Barsi')
        investor_choice = input('\nOpção: ')
        investor_map = {
            '1': 'buffett',
            '2': 'graham',
            '3': 'lynch',
            '4': 'barsi',
        }
        investor_name = investor_map.get(investor_choice)

    if not investor_name:
        print('Opção inválida!')
        exit(1)

    analysis = investor_analyze(ticker, investor_name)
    print_result(analysis, investor_name)
