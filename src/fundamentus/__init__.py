import requests
import datetime

from bs4 import BeautifulSoup


URL = "https://fundamentus.com.br"


def stock_details(ticker: str) -> dict:
    url = f"{URL}/detalhes.php?papel={ticker}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    labels = [label.find('span', class_='txt').text for label in soup.find_all('td', class_='label')]

    data = {}
    for label in labels:
        if not label:
            continue
        value = soup.find(string=label).find_next('span').text.replace('\n', '').replace(' ', '')
        dict_key = label.lower().replace(' ', '_').replace('/', '_').replace('.', '').replace('í', 'i')
        data[dict_key] = value

    return data


def stock_releases(ticker: str) -> list[dict]:
    url = f"{URL}/apresentacoes.php?papel={ticker}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all("table")
    table = tables[0]

    data = []
    for r in table.find_all("tr")[1:]:
        _tds = r.find_all("td")
        data.append(
            {
                'data': datetime.datetime.strptime(_tds[0].text.replace('\xa0', ' '), '%d/%m/%Y %H:%M').isoformat(),
                'descricao': _tds[1].text,
                'download_link': _tds[2].find('a')['href'],
            }
        )

    return data
