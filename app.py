import streamlit as st


protected_pages = [
    st.Page('pages/generate.py', title='Gerar Relatório'),
    st.Page('pages/reports.py', title='Meus Relatórios'),
    st.Page('pages/settings.py', title='Configurações'),
]

pg = st.navigation(protected_pages)
pg.run()
