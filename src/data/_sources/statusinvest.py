import requests
from typing import Literal

import pandas as pd
import unidecode
from bs4 import BeautifulSoup

URL = 'https://statusinvest.com.br'


def _fmt_col_name(name: str) -> str:
    if name == '#':
        return 'data'
    return unidecode.unidecode(name.lower().replace(' ', '_').replace('_-_(r$)', '').replace('_-_(%)', ''))


def _fmt_value(value: str) -> float | str:
    if 'Últ. 12M' in value:
        return 'ltm'

    if value == '-':
        return float('nan')

    cleaned_v = value.replace('.', '').replace(',', '.').replace(' ', '')

    if 'K' in value:
        mult = 1_000
    elif 'M' in value:
        mult = 1_000_000
    elif 'B' in value:
        mult = 1_000_000_000
    elif '%' in value:
        mult = 0.01
    else:
        mult = 1
    cleaned_v = cleaned_v.replace('K', '').replace('M', '').replace('B', '').replace('%', '')

    try:
        value_ok = round(float(cleaned_v) * mult, 4)
    except Exception as _:
        return value

    return value_ok


def _request(path: str, params: dict | None = None) -> requests.Response:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = URL + path
    r = requests.get(url, params=params, headers=headers, timeout=10)
    r.raise_for_status()
    return r


def _request_and_parse(
    path: str,
    ticker: str,
    type_: int | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> list[dict]:
    params = {'code': ticker, 'futureData': 'false'}

    if type_ is not None:
        params['type'] = type_
    if start_year is not None:
        params['range.min'] = start_year
    if end_year is not None:
        params['range.max'] = end_year

    r = _request(path, params)
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

    data = [
        {_fmt_col_name(key): _fmt_value(raw_data[key][i]) for key in raw_data}
        for i in range(len(next(iter(raw_data.values()))))
    ]

    # se annual, str year sem '.0', tipo 2020.0 > '2020'
    if type_ == 0:
        for d in data:
            if 'data' in d.keys():
                d['data'] = str(d['data']).replace('.0', '')

    return data


def details(ticker: str) -> dict:
    def _find_value(soup: BeautifulSoup, tag_name: str, text: str) -> float:
        tag = soup.find(tag_name, string=text)
        if tag:
            value_s = tag.find_next('strong', class_='value').text
            mult = 1
            if '%' in value_s:
                mult = 0.01
            try:
                if value_s == '-':
                    return float('nan')
                value = float(value_s.replace('.', '').replace(',', '.').replace('%', '')) * mult
            except ValueError as _:
                return value_s
            return value
        return None

    r = _request(f'/acoes/{ticker}', {})
    soup = BeautifulSoup(r.text, 'html.parser')

    company_div = soup.find('div', class_='company-description')
    if company_div:
        company_name = company_div.find('span', class_='text-main-green-dark').text.strip()
        cnpj = company_div.find('small', class_='fs-4').text.strip()
        site = company_div.find('a')['href']

    if not company_div:
        raise ValueError('Ticker não encontrado')

    return {
        'nome': company_name,
        'cnpj': cnpj,
        'site': site,
        'preco': _find_value(soup, 'h3', 'Valor atual'),
        'patrimonio_liquido': _find_value(soup, 'h3', 'Patrimônio líquido'),
        'ativos': _find_value(soup, 'h3', 'Ativos'),
        'ativo_circulante': _find_value(soup, 'h3', 'Ativo circulante'),
        'divida_bruta': _find_value(soup, 'h3', 'Dívida bruta'),
        'disponibilidade': _find_value(soup, 'h3', 'Disponibilidade'),
        'divida_liquida': _find_value(soup, 'h3', 'Dívida líquida'),
        'valor_de_mercado': _find_value(soup, 'h3', 'Valor de mercado'),
        'valor_de_firma': _find_value(soup, 'h3', 'Valor de firma'),
        'numero_de_acoes': _find_value(soup, 'span', 'Nº total de papéis'),
        'segmento_listagem': _find_value(soup, 'h3', 'Segmento de listagem'),
        'free_float': _find_value(soup, 'h3', 'Free Float'),
        'setor_de_atuacao': _find_value(soup, 'span', 'Setor de Atuação'),
        'subsetor_de_atuacao': _find_value(soup, 'span', 'Subsetor de Atuação'),
        'segmento_de_atuacao': _find_value(soup, 'span', 'Segmento de Atuação'),
    }


def income_statement(
    ticker: str,
    start_year: int | None = None,
    end_year: int | None = None,
    period: Literal['quarter', 'annual'] = 'quarter',
) -> list[dict]:
    _type = 0 if period == 'annual' else 1
    return _request_and_parse('/acao/getdre', ticker, _type, start_year, end_year)


def cash_flow(
    ticker: str,
    start_year: int | None = None,
    end_year: int | None = None,
    # period: Literal['quarter', 'annual'] = 'quarter',
) -> list[dict]:
    """só tem annual pq o statusinvest não tem cash flow por trimestre certo"""
    # _type = 0 if period == 'annual' else 1
    type_ = 0
    return _request_and_parse('/acao/getfluxocaixa', ticker, type_, start_year, end_year)


def balance_sheet(
    ticker: str,
    start_year: int | None = None,
    end_year: int | None = None,
    period: Literal['quarter', 'annual'] = 'quarter',
) -> list[dict]:
    _type = 0 if period == 'annual' else 1
    return _request_and_parse('/acao/getativos', ticker, _type, start_year, end_year)


def screener() -> list[dict]:
    url = f'/category/advancedsearchresultpaginated?search=%7B%22Sector%22%3A%22%22%2C%22SubSector%22%3A%22%22%2C%22Segment%22%3A%22%22%2C%22my_range%22%3A%22-20%3B100%22%2C%22forecast%22%3A%7B%22upsidedownside%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22estimatesnumber%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22revisedup%22%3Atrue%2C%22reviseddown%22%3Atrue%2C%22consensus%22%3A%5B%5D%7D%2C%22dy%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_l%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22peg_ratio%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_vp%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_ativo%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22margembruta%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22margemebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22margemliquida%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_ebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22ev_ebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22dividaliquidaebit%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22dividaliquidapatrimonioliquido%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_sr%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_capitalgiro%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22p_ativocirculante%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22roe%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22roic%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22roa%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22liquidezcorrente%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22pl_ativo%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22passivo_ativo%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22giroativos%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22receitas_cagr5%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22lucros_cagr5%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22liquidezmediadiaria%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22vpa%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22lpa%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%2C%22valormercado%22%3A%7B%22Item1%22%3Anull%2C%22Item2%22%3Anull%7D%7D&orderColumn=&isAsc=&page=0&take=610&CategoryType=1'
    r = _request(url)
    r_json = r.json()
    return r_json['list']


def multiples(ticker: str) -> dict:
    url = f'/acao/indicatorhistoricallist?codes={ticker}&time=5&byQuarter=False&futureData=False'

    r = _request(url)
    r_json = r.json()

    data = {}
    for ind_data in r_json['data'][list(r_json['data'].keys())[0]]:
        name = ind_data['key']
        hist_data = {}
        for item in ind_data['ranks']:
            v = item.get('value')
            if v is None:
                continue
            hist_data[item['rank']] = v
        data[name] = hist_data

    # tks gpt
    all_years = sorted(set(year for values in data.values() for year in values))
    transformed_data = []
    for year in all_years:
        entry = {'ano': year}
        for key in data:
            entry[key] = data[key].get(year, float('nan'))
        transformed_data.append(entry)
    return transformed_data[::-1]


def payouts(ticker: str) -> list[dict]:
    url = f'/acao/payoutresult?code={ticker}&type=2'

    r = _request(url)
    r_json = r.json()

    years = r_json['chart']['category']
    payout_values = [d['value'] for d in r_json['chart']['series']['percentual']]

    return [{'year': year, 'dividends': round(v / 100, 4)} for year, v in zip(years, payout_values) if v != 0]


def dividends(ticker: str) -> list[dict]:
    url = f'/acao/companytickerprovents?ticker={ticker}&chartProventsType=2'

    r = _request(url)
    r_json = r.json()

    return [
        {
            'data_com': d['ed'][-4:] + '-' + d['ed'][3:5] + '-' + d['ed'][:2],
            'data_pagamento': d['pd'][-4:] + '-' + d['pd'][3:5] + '-' + d['pd'][:2],
            'valor': d['v'],
        }
        for d in r_json['assetEarningsModels']
    ]
