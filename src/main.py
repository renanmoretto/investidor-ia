import json
import base64
import io
import datetime
import os
from typing import Literal, Any

import requests
import yfinance as yf
import pandas as pd
import polars as pl
import unidecode
from bs4 import BeautifulSoup
from google import genai
from dotenv import load_dotenv
from pydantic import BaseModel
from rich.console import Console
from rich.markdown import Markdown
from rich.pretty import pprint
from rich.table import Table

from src import b3, fundamentus, statusinvest
from src.agents.analysts import (
    earnings_release_analyst,
    financial_analyst,
    valuation_analyst,
    news_analyst,
)
from src.agents.investors import graham
from src.llm import ask
from src.agents.base import BaseAgentOutput


def _calc_cagr(data: dict, name: str, length: int = 5) -> float:
    _data = [d for d in data if name in d['index']][0]
    values = list(_data.values())[1:][::-1][-length:]
    return round((values[-1] / values[0]) ** (1 / (len(values) - 1)) - 1, 4)


def print_result():
    # TODO
    pass


async def investor_analyze(
    ticker: str,
    investor_name: str,
):
    today = datetime.date.today()
    year_start = today.year - 5
    year_end = today.year

    # get all data
    print(f'Coletando dados da empresa {ticker}...')
    b3_details = b3.get_company_data(ticker)
    company_name = b3_details.get('companyName', 'nan')
    stock_details = fundamentus.stock_details(ticker)
    stock_releases = fundamentus.stock_releases(ticker)
    dre_quarter = statusinvest.dre(ticker, year_start, year_end, 'quarter')
    dre_year = statusinvest.dre(ticker, year_start, year_end, 'year')
    cash_flow_year = statusinvest.cash_flow(ticker, year_start, year_end, 'year')
    cash_flow_quarter = statusinvest.cash_flow(ticker, year_start, year_end, 'quarter')
    balance_sheet_year = statusinvest.balance_sheet(ticker, year_start, year_end, 'year')
    balance_sheet_quarter = statusinvest.balance_sheet(ticker, year_start, year_end, 'quarter')
    screener_statusinvest = statusinvest.screener()
    dividends = fundamentus.stock_dividends(ticker)
    cagr_5y_receita_liq = _calc_cagr(dre_year, 'receita_liquida', 5)
    cagr_5y_lucro_liq = _calc_cagr(dre_year, 'lucro_liquido', 5)
    dividends_by_year = (
        pl.DataFrame(dividends)
        .with_columns(year=pl.col('data_pagamento').str.slice(0, 4).cast(pl.Int64))
        .group_by('year')
        .agg(pl.col('valor').sum().round(4))
        .sort('year')
        .to_dicts()
    )
    dividends_growth = (
        pl.DataFrame(dividends_by_year)
        .with_columns(valor=pl.col('valor').pct_change().round(4))
        .drop_nulls()
        .to_dicts()
    )

    release_link = stock_releases[0]['download_link']
    r = requests.get(release_link)
    release_pdf_bytes = r.content

    # status invest screener
    screener_statusinvest_df = (
        pl.DataFrame(screener_statusinvest)
        .with_columns(stock=pl.col('ticker').str.slice(0, 4))
        .sort('stock', 'liquidezmediadiaria')  # pega apenas o ticker que tem mais liquidez
        .unique('stock', keep='last')
        .filter(pl.col('price') > 0, pl.col('liquidezmediadiaria') > 0)
    )
    _stock_segment = screener_statusinvest_df.filter(pl.col('ticker') == ticker)['segmentname'][0]

    segment_means = screener_statusinvest_df.filter(pl.col('segmentname') == _stock_segment).mean()
    segment_medians = screener_statusinvest_df.filter(pl.col('segmentname') == _stock_segment).median()
    stock_multiples = screener_statusinvest_df.filter(pl.col('ticker') == ticker)
    market_multiples_median = (
        screener_statusinvest_df.filter(
            pl.col('valormercado') > 1e9,
            pl.col('liquidezmediadiaria') > 1e6,
        )
        .sort('liquidezmediadiaria', descending=True)
        .median()
    )

    # ai analysts
    print('Analisando earnings release...')
    earnings_release_analysis = await earnings_release_analyst.analyze(
        ticker=ticker,
        company_name=company_name,
        earnings_release_pdf_bytes=release_pdf_bytes,
    )

    print('Analisando dados financeiros...')
    financial_analysis = await financial_analyst.analyze(
        ticker=ticker,
        company_name=company_name,
        segment=b3_details.get('segment', 'nan'),
        dre_quarter=pd.DataFrame(dre_quarter).set_index('index').to_dict(),
        cash_flow_quarter=pd.DataFrame(cash_flow_quarter).set_index('index').to_dict(),
        balance_sheet_quarter=pd.DataFrame(balance_sheet_quarter).set_index('index').to_dict(),
        stock_details=stock_details,
        cagr_5y_receita_liq=cagr_5y_receita_liq,
        cagr_5y_lucro_liq=cagr_5y_lucro_liq,
        dividends_by_year=dividends_by_year,
        dividends_growth=dividends_growth,
    )

    print('Analisando valuation...')
    valuation_analysis = await valuation_analyst.analyze(
        ticker=ticker,
        company_name=company_name,
        segment=b3_details.get('segment', 'nan'),
        current_price=stock_details.get('price', float('nan')),
        current_multiples=stock_multiples.to_dicts()[0],
        historical_multiples=stock_multiples.to_dicts()[0],
        sector_multiples_mean=segment_means.to_dicts()[0],
        sector_multiples_median=segment_medians.to_dicts()[0],
        market_multiples_median=market_multiples_median.to_dicts()[0],
    )

    print('Analisando notícias...')
    news_analysis = await news_analyst.analyze(
        ticker=ticker,
        company_name=company_name,
    )

    # investor analysis
    print('Juntando análises e gerando resposta final...')
    if investor_name == 'buffett':
        pass
    elif investor_name == 'graham':
        classic_criteria = {
            'valor_de_mercado': f'{stock_details.get("valor_de_mercado", float("nan")):,.0f} BRL',
            'preco_sobre_lucro': stock_details.get('p_l', float('nan')),
            'preco_sobre_lucro_abaixo_15x': stock_details.get('p_l', float('nan')) < 15,
            'preco_sobre_valor_patrimonial': stock_details.get('p_vp', float('nan')),
            'preco_sobre_valor_patrimonial_abaixo_1.5x': stock_details.get('p_vp', float('nan')) < 1.5,
            'divida_bruta': stock_details.get('div_bruta', float('nan')),
            'patrimonio_liquido': stock_details.get('patrim_liq', float('nan')),
            'divida_menor_que_patrimonio_liquido': stock_details.get('div_liq', float('nan'))
            < stock_details.get('patrim_liq', float('nan')),
            'crescimento_dividendos_anuais': dividends_growth,
            'lucro_liquido_positivo_nos_ultimos_5_anos': all(
                [v > 0 for v in list([d for d in dre_year if 'lucro_liquido' in d['index']][0].values())[1:]]
            ),
            'cagr_5y_receita_liq': cagr_5y_receita_liq,
            'cagr_5y_lucro_liq': cagr_5y_lucro_liq,
            'ativo_circulante_sobre_passivo_circulante': pl.DataFrame(balance_sheet_quarter)
            .transpose(include_header=True, column_names='index')
            .head(1)
            .with_columns(v=pl.col('ativo_circulante') / pl.col('passivo_circulante'))['v']
            .round(4)[0],
        }
        investor_analysis = await graham.analyze(
            ticker=ticker,
            company_name=company_name,
            segment=b3_details.get('segment', 'nan'),
            earnings_release_analysis=earnings_release_analysis,
            financial_analysis=financial_analysis,
            valuation_analysis=valuation_analysis,
            news_analysis=news_analysis,
            dre_year=dre_year,
            classic_criteria=classic_criteria,
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


if __name__ == '__main__':
    pass
