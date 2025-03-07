import requests
from typing import Literal

import pandas as pd


URL = 'https://statusinvest.com.br'


def _request_and_parse(path: str, ticker: str, type_: int, start_year: int, end_year: int) -> dict:
    url = URL + f'/acao/{path}?code={ticker}&type={type_}&futureData=false&range.min={start_year}&range.max={end_year}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    r = requests.get(url, headers=headers)
    r_json = r.json()
    grid_data = r_json['data']['grid']

    raw_data = {}
    for grid_data_items in grid_data[:]:
        col_name = grid_data_items['columns'][0]['value']
        for item in grid_data_items['columns'][1:]:
            if item.get('name') in ['AH', 'AV']:
                continue
            col_values = raw_data.get(col_name, [])
            col_values.append(item['value'])
            raw_data[col_name] = col_values

    data = pd.DataFrame(raw_data).set_index('#').T.reset_index().to_dict('records')
    return data


def dre(ticker: str, start_year: int, end_year: int, period: Literal['quarter', 'year'] = 'quarter') -> dict:
    _type = 0 if period == 'year' else 1
    return _request_and_parse('getdre', ticker, _type, start_year, end_year)


def cash_flow(ticker: str, start_year: int, end_year: int) -> dict:
    return _request_and_parse('getfluxocaixa', ticker, 0, start_year, end_year)


def balance_sheet(ticker: str, start_year: int, end_year: int) -> dict:
    return _request_and_parse('getativos', ticker, 0, start_year, end_year)