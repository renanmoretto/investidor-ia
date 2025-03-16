import streamlit as st
import json
import os
from src.settings import DB_DIR, reload_api_keys


st.set_page_config(layout='centered')


st.title('Configurações')

st.divider()


def _get_api_key(api_name) -> str | None:
    try:
        with open(os.path.join(DB_DIR, 'api_keys.json'), 'r') as f:
            api_keys = json.load(f)
        return api_keys.get(api_name)
    except FileNotFoundError:
        return None


def _save_api_key(api_name, api_key):
    try:
        with open(os.path.join(DB_DIR, 'api_keys.json'), 'r') as f:
            api_keys = json.load(f)
    except FileNotFoundError:
        api_keys = {}

    api_keys[api_name] = api_key

    with open(os.path.join(DB_DIR, 'api_keys.json'), 'w') as f:
        json.dump(api_keys, f)


gemini_key = st.text_input('GEMINI API KEY', type='password', value=_get_api_key('gemini'))

if st.button('Salvar'):
    _save_api_key('gemini', gemini_key)
    st.success('API Key salva com sucesso!')
    reload_api_keys()
