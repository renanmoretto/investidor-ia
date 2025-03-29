import streamlit as st
import json
import os


from src.settings import DB_DIR, reload_api_keys, get_api_key


st.set_page_config(layout='centered')


st.title('Configurações')

st.divider()


def _save_api_key(api_name, api_key):
    try:
        with open(os.path.join(DB_DIR, 'api_keys.json'), 'r') as f:
            api_keys = json.load(f)
    except FileNotFoundError:
        api_keys = {}

    api_keys[api_name] = api_key

    with open(os.path.join(DB_DIR, 'api_keys.json'), 'w') as f:
        json.dump(api_keys, f)


gemini_key = st.text_input('GEMINI API KEY', type='password', value=get_api_key('gemini'))
# openai_key = st.text_input('OPENAI API KEY', type='password', value=get_api_key('openai'))

if st.button('Salvar'):
    _save_api_key('gemini', gemini_key)
    # _save_api_key('openai', openai_key)
    st.success('API Key salva com sucesso!')
    reload_api_keys()
