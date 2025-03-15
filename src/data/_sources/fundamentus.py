import requests
import datetime

from bs4 import BeautifulSoup


URL = 'https://fundamentus.com.br'


def _request(url: str) -> requests.Response:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    return response


def detalhes(ticker: str) -> dict:
    response = _request(f'{URL}/detalhes.php?papel={ticker}')

    soup = BeautifulSoup(response.text, 'html.parser')
    labels = [label.find('span', class_='txt').text for label in soup.find_all('td', class_='label')]

    data = {}
    for label in labels:
        if not label:
            continue
        value = soup.find(string=label).find_next('span').text.replace('\n', '').replace(' ', '')
        dict_key = label.lower().replace(' ', '_').replace('/', '_').replace('.', '').replace('í', 'i')
        data[dict_key] = value

    # values to float
    for k, v in data.items():
        try:
            # Skip if string contains 2 or more letters (real string value)
            letter_count = sum(c.isalpha() for c in v)
            if letter_count > 2:
                continue

            v = v.replace('.', '').replace(',', '.').replace(' ', '').replace('M', '')
            if '%' in v:
                v = float(v.replace('%', '')) / 100
            else:
                v = float(v)
            data[k] = round(v, 4)
        except:
            pass

    return data


def proventos(ticker: str) -> list[dict]:
    response = _request(f'{URL}/proventos.php?papel={ticker}')

    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all('table')
    if not tables:
        return []

    table = tables[0]

    data = []
    for r in table.find_all('tr')[1:]:
        _tds = r.find_all('td')
        try:
            data.append(
                {
                    'data': datetime.datetime.strptime(_tds[0].text.replace('\xa0', ' '), '%d/%m/%Y')
                    .date()
                    .isoformat(),
                    'data_pagamento': datetime.datetime.strptime(
                        _tds[3].text.replace('\t', '').replace(' ', ''), '%d/%m/%Y'
                    )
                    .date()
                    .isoformat(),
                    'valor': float(_tds[1].text.replace('.', '').replace(',', '.').replace(' ', '')),
                }
            )
        except Exception as _:
            pass

    return data


def resultados_trimestrais(ticker: str) -> list[dict]:
    response = _request(f'{URL}/resultados_trimestrais.php?papel={ticker}')

    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all('table')
    table = tables[0]

    data = []
    for r in table.find_all('tr')[1:]:
        _tds = r.find_all('td')
        try:
            link_cvm = _tds[1].find('a')['href']
        except Exception as _:
            link_cvm = None
        try:
            download_link = _tds[2].find('a')['href']
        except Exception as _:
            download_link = None
        data.append(
            {
                'data': datetime.datetime.strptime(_tds[0].text.replace('\xa0', ' '), '%d/%m/%Y').isoformat(),
                'link_cvm': link_cvm,
                'download_link': download_link,
            }
        )

    return data


def apresentacoes(ticker: str) -> list[dict]:
    response = _request(f'{URL}/apresentacoes.php?papel={ticker}')

    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all('table')
    table = tables[0]

    data = []
    for r in table.find_all('tr')[1:]:
        _tds = r.find_all('td')
        try:
            download_link = _tds[2].find('a')['href']
        except Exception as _:
            download_link = None
        data.append(
            {
                'data': datetime.datetime.strptime(_tds[0].text.replace('\xa0', ' '), '%d/%m/%Y %H:%M').isoformat(),
                'descricao': _tds[1].text,
                'download_link': download_link,
            }
        )

    return data
