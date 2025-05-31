import datetime
import json
import os
from pathlib import Path

from pydantic import BaseModel
import streamlit as st

from src.data import stocks
from src.agents.analysts import (
    earnings_release,
    financial,
    valuation,
    news,
)
from src.agents.investors import (
    buffett,
    graham,
    barsi,
)
from src.settings import DB_DIR, INVESTORS, PROVIDER, MODEL, API_KEY
from pages._utils import Report, display_report


if not PROVIDER or not MODEL or not API_KEY:
    st.error('Por favor, configure o modelo e a chave de API no menu de configurações')
    st.stop()


st.set_page_config(layout='centered')


def _generate_investor_report(
    ticker: str,
    investor_name: str,
) -> Report | None:
    if investor_name not in INVESTORS.keys():
        st.error(f'Investidor {investor_name} não encontrado')
        return

    ticker = ticker.upper()

    # verifica se o ticker existe
    try:
        stocks.details(ticker)
    except ValueError:
        st.error(f'Ticker {ticker} não encontrado')
        return

    # ai analysts
    with st.spinner('Analisando earnings release...'):
        earnings_release_analysis = earnings_release.analyze(ticker)

    with st.spinner('Analisando dados financeiros...'):
        financial_analysis = financial.analyze(ticker)

    with st.spinner('Analisando valuation...'):
        valuation_analysis = valuation.analyze(ticker)

    with st.spinner('Analisando notícias...'):
        news_analysis = news.analyze(ticker=ticker)

    # final investor analysis
    with st.spinner('Gerando relatório final...'):
        if investor_name == 'buffett':
            investor_analysis = buffett.analyze(
                ticker=ticker,
                earnings_release_analysis=earnings_release_analysis,
                financial_analysis=financial_analysis,
                valuation_analysis=valuation_analysis,
                news_analysis=news_analysis,
            )

        elif investor_name == 'graham':
            investor_analysis = graham.analyze(
                ticker=ticker,
                earnings_release_analysis=earnings_release_analysis,
                financial_analysis=financial_analysis,
                valuation_analysis=valuation_analysis,
                news_analysis=news_analysis,
            )

        elif investor_name == 'barsi':
            investor_analysis = barsi.analyze(
                ticker=ticker,
                earnings_release_analysis=earnings_release_analysis,
                financial_analysis=financial_analysis,
                valuation_analysis=valuation_analysis,
                news_analysis=news_analysis,
            )

        else:
            raise ValueError(f'Investor {investor_name} not found')

    report_data = {
        'analysts': {
            'earnings_release': earnings_release_analysis.model_dump(),
            'financial': financial_analysis.model_dump(),
            'valuation': valuation_analysis.model_dump(),
            'news': news_analysis.model_dump(),
        },
        'investor': investor_analysis.model_dump(),
    }
    return Report(
        ticker=ticker,
        investor_name=investor_name,
        generated_at=datetime.datetime.now(),
        data=report_data,
    )


def _load_reports() -> list[Report]:
    reports_file = Path('db/reports.json')
    if reports_file.exists():
        with open(reports_file, 'r') as f:
            content = f.read()
            reports = json.loads(content) if content else []
            if reports:
                return reports
    return []


def _save_report(report: Report):
    reports_file = DB_DIR / 'reports.json'

    report_dict = json.loads(report.model_dump_json())

    reports = _load_reports()
    reports.append(report_dict)

    with open(reports_file, 'w') as f:
        json.dump(reports, f, indent=4)


st.title('Gerar Relatório')


ticker = st.text_input('Ticker da ação')
investor = st.selectbox('Investidor', list(INVESTORS.values()))

try:
    investor_name = {v: k for k, v in INVESTORS.items()}[investor]
except KeyError:
    st.error(f'Investidor {investor} não encontrado')
    investor_name = None

result = None
if st.button('Gerar Relatório'):
    result = _generate_investor_report(ticker, investor_name)
    _save_report(result)
    display_report(result)
