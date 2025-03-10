import requests
from typing import Literal

import pandas as pd
import unidecode


URL = 'https://statusinvest.com.br'


def _transform_data(data: dict) -> list[dict]:
    result = []

    for d in data:
        transformed_dict = {}

        for k, v in d.items():
            if k == 'index':
                value = unidecode.unidecode(v.lower().replace(' ', '_').replace('_-_(r$)', '').replace('_-_(%)', ''))
            elif v == '-':
                value = float('nan')
            else:
                # Clean up the value string
                cleaned_v = v.replace('.', '').replace(',', '.').replace(' ', '')

                if '%' in v:
                    # Handle percentage values
                    cleaned_v = cleaned_v.replace('%', '')
                    value = float(cleaned_v) / 100
                else:
                    # Handle monetary values with M suffix
                    if 'M' in v:
                        mult = 1_000_000
                    elif 'B' in v:
                        mult = 1_000_000_000
                    else:
                        mult = 1
                    cleaned_v = cleaned_v.replace('M', '').replace('B', '')
                    value = float(cleaned_v) * mult

            if 'Últ. 12M' in k:
                k = 'ltm'

            transformed_dict[k] = value

        result.append(transformed_dict)

    return result


def _request_and_parse(path: str, ticker: str, type_: int, start_year: int, end_year: int) -> list[dict]:
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
    return _transform_data(data)


def dre(ticker: str, start_year: int, end_year: int, period: Literal['quarter', 'year'] = 'quarter') -> list[dict]:
    _type = 0 if period == 'year' else 1
    return _request_and_parse('getdre', ticker, _type, start_year, end_year)


def cash_flow(
    ticker: str, start_year: int, end_year: int, period: Literal['quarter', 'year'] = 'quarter'
) -> list[dict]:
    _type = 0 if period == 'year' else 1
    return _request_and_parse('getfluxocaixa', ticker, _type, start_year, end_year)


def balance_sheet(
    ticker: str, start_year: int, end_year: int, period: Literal['quarter', 'year'] = 'quarter'
) -> list[dict]:
    _type = 0 if period == 'year' else 1
    return _request_and_parse('getativos', ticker, _type, start_year, end_year)


def screener() -> list[dict]:
    url = 'https://statusinvest.com.br/category/advancedsearchresultpaginated?search=%7B%22Sector%22%3A%22%22%2C%22SubSector%22%3A%22%22%2C%22Segment%22%3A%22%22%2C%22my_range%22%3A%22-20%3B100%22%2C%22forecast%22%3A%7B%22upsidedownside%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22estimatesnumber%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22revisedup%22%3Atrue%2C%22reviseddown%22%3Atrue%2C%22consensus%22%3A%5B%5D%7D%2C%22dy%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_l%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22peg_ratio%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_vp%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_ativo%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22margembruta%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22margemebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22margemliquida%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_ebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22ev_ebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22dividaliquidaebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22dividaliquidapatrimonioliquido%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_sr%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_capitalgiro%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_ativocirculante%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22roe%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22roic%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22roa%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22liquidezcorrente%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22pl_ativo%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22passivo_ativo%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22giroativos%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22receitas_cagr5%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22lucros_cagr5%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22liquidezmediadiaria%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22vpa%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22lpa%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22valormercado%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%7D&orderColumn=&isAsc=&page=0&take=610&CategoryType=1'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    r = requests.get(url, headers=headers)
    r_json = r.json()
    return r_json['list']


def indicator_history(ticker: str) -> dict:
    url = 'https://statusinvest.com.br/acao/indicatorhistoricallist'
    data = {'codes[]': ticker.lower(), 'time': 5, 'byQuarter': False, 'futureData': False}

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    }

    r = requests.post(url, data=data, headers=headers)
    r_json = r.json()

    data = {}
    for ind_data in r_json['data'][ticker.lower()]:
        name = ind_data['key']
        hist_data = {}
        for item in ind_data['ranks']:
            v = item.get('value')
            if v is None:
                continue
            hist_data[item['rank']] = v
        data[name] = hist_data

    return data
