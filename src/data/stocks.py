from typing import Literal

from src.cache import cache_it
from ._sources import b3, statusinvest, fundamentus


@cache_it
def company_details(ticker: str) -> dict:
    return b3.get_company_data(ticker)


def company_name(ticker: str) -> str:
    return company_details(ticker)['companyName']


def earnings_releases(ticker: str) -> list[str]:
    return fundamentus.earnings_releases(ticker)


def income_statement(
    ticker: str,
    year_start: int | None = None,
    year_end: int | None = None,
    period: Literal['annual', 'quarter'] = 'annual',
) -> dict:
    return statusinvest.dre(ticker, year_start, year_end, period)


def balance_sheet(
    ticker: str,
    year_start: int | None = None,
    year_end: int | None = None,
    period: Literal['annual', 'quarter'] = 'annual',
) -> dict:
    return statusinvest.balance_sheet(ticker, year_start, year_end, period)


def cash_flow(
    ticker: str,
    year_start: int | None = None,
    year_end: int | None = None,
    period: Literal['annual', 'quarter'] = 'annual',
) -> dict:
    return statusinvest.cash_flow(ticker, year_start, year_end, period)


def multiples(ticker: str) -> dict:
    return statusinvest.multiples(ticker)


def dividends(ticker: str) -> list[dict]:
    return fundamentus.stock_dividends(ticker)


def screener():
    return statusinvest.screener()
