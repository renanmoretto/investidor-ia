from typing import Literal

from src.cache import cache_it
from ._sources import b3, statusinvest, fundamentus


@cache_it
async def details(ticker: str) -> dict:
    return await statusinvest.details(ticker)


@cache_it
async def name(ticker: str) -> str:
    return (await details(ticker))['nome']


@cache_it
async def income_statement(
    ticker: str,
    year_start: int | None = None,
    year_end: int | None = None,
    period: Literal['annual', 'quarter'] = 'annual',
) -> dict:
    return await statusinvest.income_statement(ticker, year_start, year_end, period)


@cache_it
async def balance_sheet(
    ticker: str,
    year_start: int | None = None,
    year_end: int | None = None,
    period: Literal['annual', 'quarter'] = 'annual',
) -> dict:
    return await statusinvest.balance_sheet(ticker, year_start, year_end, period)


@cache_it
async def cash_flow(
    ticker: str,
    year_start: int | None = None,
    year_end: int | None = None,
    # period: Literal['annual', 'quarter'] = 'annual',
) -> dict:
    return await statusinvest.cash_flow(ticker, year_start, year_end)


@cache_it
async def multiples(ticker: str) -> dict:
    return await statusinvest.multiples(ticker)


@cache_it
async def dividends(ticker: str) -> list[dict]:
    # return fundamentus.proventos(ticker)
    return await statusinvest.dividends(ticker)


@cache_it
async def dividends_by_year(ticker: str) -> list[dict]:
    stock_dividends = await dividends(ticker)
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
async def screener():
    return await statusinvest.screener()


@cache_it
async def payouts(ticker: str) -> list[dict]:
    return await statusinvest.payouts(ticker)
