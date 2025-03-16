from typing import Literal

from src.cache import cache_it
from ._sources import b3, statusinvest, fundamentus


@cache_it
def details(ticker: str) -> dict:
    return statusinvest.details(ticker)


@cache_it
def name(ticker: str) -> str:
    return details(ticker)['nome']


@cache_it
def income_statement(
    ticker: str,
    year_start: int | None = None,
    year_end: int | None = None,
    period: Literal['annual', 'quarter'] = 'annual',
) -> dict:
    return statusinvest.income_statement(ticker, year_start, year_end, period)


@cache_it
def balance_sheet(
    ticker: str,
    year_start: int | None = None,
    year_end: int | None = None,
    period: Literal['annual', 'quarter'] = 'annual',
) -> dict:
    return statusinvest.balance_sheet(ticker, year_start, year_end, period)


@cache_it
def cash_flow(
    ticker: str,
    year_start: int | None = None,
    year_end: int | None = None,
    # period: Literal['annual', 'quarter'] = 'annual',
) -> dict:
    return statusinvest.cash_flow(ticker, year_start, year_end)


@cache_it
def multiples(ticker: str) -> dict:
    return statusinvest.multiples(ticker)


@cache_it
def dividends(ticker: str) -> list[dict]:
    # return fundamentus.proventos(ticker)
    return statusinvest.dividends(ticker)


@cache_it
def dividends_by_year(ticker: str) -> list[dict]:
    stock_dividends = dividends(ticker)
    yearly_dividends = {}
    for dividend in stock_dividends:
        if dividend['data_pagamento'] == '----':
            continue
        year = int(dividend['data_pagamento'][:4])
        if year not in yearly_dividends:
            yearly_dividends[year] = 0
        yearly_dividends[year] += dividend['valor']

    return [{'ano': year, 'valor': round(value, 8)} for year, value in sorted(yearly_dividends.items())]


@cache_it
def screener():
    return statusinvest.screener()


@cache_it
def payouts(ticker: str) -> list[dict]:
    return statusinvest.payouts(ticker)
