import streamlit as st

from src.chat.agent import get_chat_agent
from src.settings import PROVIDER, MODEL, API_KEY, reload_llm_config

reload_llm_config()


if not PROVIDER or not MODEL or not API_KEY:
    st.error('Por favor, configure o modelo e a chave de API no menu de configurações')
    st.stop()


st.set_page_config(layout='centered')

st.title('Chat')

if st.button('Novo chat'):
    st.session_state.messages = []

investor = st.selectbox('Selecione o investidor', ['Buffett', 'Graham', 'Barsi'])

agent = get_chat_agent(investor=investor.lower())


if 'messages' not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.markdown(message['content'].replace('$', r'\$'))

if prompt := st.chat_input('Digite uma mensagem'):
    st.chat_message('user').markdown(prompt.replace('$', r'\$'))
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    with st.chat_message('assistant'):
        msg_placeholder = st.empty()
        response = agent.run(prompt, messages=st.session_state.messages, markdown=True, stream=True)
        full_response = ''
        for chunk in response:
            full_response += chunk.content or ''
            msg_placeholder.markdown(full_response.replace('$', r'\$'))
    st.session_state.messages.append({'role': 'assistant', 'content': full_response})
    print(f'chat > {prompt}')
    print(f'chat > {full_response}')
    print(f'chat > {agent.run_response.metrics}')  # type: ignore
