import datetime

import streamlit as st
from pydantic import BaseModel


class Report(BaseModel):
    ticker: str
    investor_name: str
    generated_at: datetime.datetime
    data: dict


def display_report(report: Report):
    def _make_expander_analyst(analyst_name: str, analysis: dict):
        with st.expander(f'Opinião do analista de {analyst_name} - {analysis["sentiment"]}', expanded=False):
            st.markdown(f'Confiança: {analysis["confidence"]}%')
            # esse replace é para evitar que o streamlit interprete o $ como LaTeX
            st.markdown(analysis['content'].replace('$', '\$'))

    analysts = report.data['analysts']

    _make_expander_analyst('Earnings Release', analysts['earnings_release'])
    _make_expander_analyst('Financial', analysts['financial'])
    _make_expander_analyst('Valuation', analysts['valuation'])
    _make_expander_analyst('News', analysts['news'])

    sentiment = report.data['investor']['sentiment']
    sentiment_color = {'BULLISH': 'green', 'NEUTRAL': 'yellow', 'BEARISH': 'red'}[sentiment]
    st.markdown(
        f'<h1>Sentimento: <span style="color: {sentiment_color}">{sentiment}</span></h1>',
        unsafe_allow_html=True,
    )
    st.markdown(f'# Confiança: {report.data["investor"]["confidence"]}%')
    st.markdown(report.data['investor']['content'].replace('$', '\$'))

    # disclaimer
    st.divider()
    st.markdown('<small style="color: red">**Disclaimer:**</small>', unsafe_allow_html=True)
    st.markdown(
        '<small style="color: gray">'
        + 'Este relatório foi gerado por um sistema de Inteligência Artificial e NÃO constitui recomendação de investimento. '
        + 'As análises apresentadas são meramente informativas e não devem ser utilizadas como única base para decisões de investimento. '
        + 'Os desenvolvedores e o sistema não se responsabilizam por eventuais perdas ou ganhos decorrentes do uso destas informações. '
        + 'Investimentos em renda variável envolvem riscos e podem resultar em perdas patrimoniais.'
        + '</small>',
        unsafe_allow_html=True,
    )
