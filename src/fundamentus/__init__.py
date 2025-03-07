import requests
from bs4 import BeautifulSoup


def get_stock_details(ticker: str) -> dict:
    url = f"https://fundamentus.com.br/detalhes.php?papel={ticker}"
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