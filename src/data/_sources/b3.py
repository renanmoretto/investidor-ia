import json
import base64

import requests


def get_company_data(ticker: str) -> dict:
    """Acha dados da companhia no site da B3, como nome, código CVM, etc."""
    url = 'https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetInitialCompanies/'
    data = {
        'language': 'pt-br',
        'pageNumber': 1,
        'pageSize': 20,
        'company': ticker,
    }
    data_b64_string = base64.b64encode(json.dumps(data).encode('utf-8')).decode('utf-8')

    r = requests.get(url + data_b64_string)
    r.raise_for_status()
    r_json = r.json()

    # find company data
    company_data = {}
    for result in r_json['results']:
        if result['issuingCompany'] == ticker[:4]:
            company_data = result
            # print(f'ticker encontrado: {company_data["companyName"]}')
            break
    else:
        raise ValueError(f'Ticker {ticker} not found')
    company_data['ticker'] = ticker

    return company_data