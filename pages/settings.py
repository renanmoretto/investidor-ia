import streamlit as st
import json
import os
from src.settings import DB_DIR, reload_api_keys


st.set_page_config(layout='centered')


st.title('Configurações')

st.divider()


def _get_api_key(api_name):
    with open(os.path.join(DB_DIR, 'api_keys.json'), 'r') as f:
        api_keys = json.load(f)
    return api_keys.get(api_name)


# Input para API KEY do Gemini
gemini_key = st.text_input('GEMINI API KEY', type='password', value=_get_api_key('gemini'))

# Botão de salvar
if st.button('Salvar'):
    # Criar diretório se não existir
    os.makedirs(DB_DIR, exist_ok=True)

    # Salvar API key em um arquivo JSON
    api_keys = {'gemini': gemini_key}
    with open(os.path.join(DB_DIR, 'api_keys.json'), 'w') as f:
        json.dump(api_keys, f)

    st.success('API Key salva com sucesso!')
    reload_api_keys()
