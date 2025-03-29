import os
import sys
import subprocess

import streamlit as st


protected_pages = [
    st.Page('pages/chat.py', title='Chat'),
    st.Page('pages/generate.py', title='Gerar Relatório'),
    st.Page('pages/reports.py', title='Meus Relatórios'),
    st.Page('pages/settings.py', title='Configurações'),
]

pg = st.navigation(protected_pages)
pg.run()


if __name__ == '__main__':
    # Obtém o caminho absoluto do diretório atual
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Caminho para o arquivo app.py
    app_path = os.path.join(current_dir, 'app.py')

    # Executa o comando streamlit run app.py
    subprocess.run([sys.executable, '-m', 'streamlit', 'run', app_path])
