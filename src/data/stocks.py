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
def earnings_releases(ticker: str) -> list[str]:
    return fundamentus.earnings_releases(ticker)


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
    period: Literal['annual', 'quarter'] = 'annual',
) -> dict:
    return statusinvest.cash_flow(ticker, year_start, year_end, period)


@cache_it
def multiples(ticker: str) -> dict:
    return statusinvest.multiples(ticker)


@cache_it
def dividends(ticker: str) -> list[dict]:
    return fundamentus.stock_dividends(ticker)


@cache_it
def screener():
    return statusinvest.screener()
