import json
from pathlib import Path

import streamlit as st

from src.settings import INVESTORS, DB_DIR
from pages._utils import Report, display_report


st.set_page_config(layout='centered')


def _load_reports() -> list[Report]:
    reports_file = DB_DIR / 'reports.json'
    if reports_file.exists():
        with open(reports_file, 'r') as f:
            content = f.read()
            reports = json.loads(content) if content else []
            if reports:
                return [Report(**report) for report in reports]
    return []


def _save_reports(reports: list[Report]):
    reports_file = DB_DIR / 'reports.json'
    with open(reports_file, 'w') as f:
        json_reports = [json.loads(report.model_dump_json()) for report in reports]
        json.dump(json_reports, f)


def _delete_report(report: Report):
    reports = _load_reports()
    for i, _report in enumerate(reports):
        if report == _report:
            reports.pop(i)
            break
    _save_reports(reports)


@st.dialog(title='Excluir Relatório')
def _delete_dialog(report: Report):
    st.title('Deletar Relatório?')
    col1, col2 = st.columns(2)
    with col1:
        if st.button('Sim'):
            _delete_report(report)
            st.rerun()
    with col2:
        if st.button('Não'):
            st.rerun()


# page


reports = _load_reports()

if not reports:
    st.write('Nenhum relatório encontrado')
    st.stop()

report = st.selectbox(
    label='Selecione um relatório',
    options=reports,
    format_func=lambda x: f'{x.ticker} - {INVESTORS.get(x.investor_name, x.investor_name)} - {x.generated_at.strftime("%d/%m/%Y %H:%M")}',
    index=None,
    placeholder='Selecione um relatório',
    label_visibility='hidden',
)

st.markdown('')

if report:
    display_report(report)
    if st.button('Excluir relatório', type='tertiary'):
        _delete_dialog(report)
