import streamlit as st
import json
import os

from src.settings import DB_DIR, reload_llm_config, get_llm_config


st.set_page_config(layout='centered')


st.title('Configurações')

st.divider()


def _get_api_key(provider: str) -> str | None:
    with open(os.path.join(DB_DIR, 'api_keys.json'), 'r') as f:
        api_keys = json.load(f)
    return api_keys.get(provider)


def _get_provider_and_model() -> tuple[str, str] | None:
    with open(os.path.join(DB_DIR, 'model.json'), 'r') as f:
        model = json.load(f)
    return model.get('provider'), model.get('model')


def _save_api_keys(api_keys: dict[str, str]):
    with open(os.path.join(DB_DIR, 'api_keys.json'), 'w') as f:
        json.dump(api_keys, f)


def _save_model(provider, model):
    with open(os.path.join(DB_DIR, 'model.json'), 'w') as f:
        json.dump({'provider': provider, 'model': model}, f)


st.markdown('### Provedor e Modelo')

provider, model = _get_provider_and_model()

provider_options = ['GOOGLE', 'OPENAI', 'OPENROUTER']
provider = st.selectbox('Provedor', provider_options, index=provider_options.index(provider))
model = st.text_input('Modelo', value=model)

st.divider()

st.markdown('### API Keys')

google_key = st.text_input('GOOGLE API KEY', type='password', value=_get_api_key('GOOGLE'))
openai_key = st.text_input('OPENAI API KEY', type='password', value=_get_api_key('OPENAI'))
openrouter_key = st.text_input('OPENROUTER API KEY', type='password', value=_get_api_key('OPENROUTER'))

st.divider()

if st.button('Salvar'):
    _save_api_keys(
        {
            'GOOGLE': google_key,
            'OPENAI': openai_key,
            'OPENROUTER': openrouter_key,
        }
    )
    _save_model(provider, model)
    st.success('Configurações salvas com sucesso!')
    reload_llm_config()
