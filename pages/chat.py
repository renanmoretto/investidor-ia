import streamlit as st

from src.chat.agent import get_chat_agent
from src.settings import get_api_key


st.set_page_config(layout='centered')

st.title('Chat')

if st.button('Novo chat'):
    st.session_state.messages = []

investor = st.selectbox('Selecione o investidor', ['Buffett', 'Graham', 'Barsi'])

agent = get_chat_agent(investor=investor.lower())

if not get_api_key('gemini'):
    st.error(
        'Não foi encontrada uma chave de API para o Gemini. Se você já inseriu uma chave de API, dê um refresh na página.'
    )
    st.page_link('pages/settings.py', label='Acesse a página de configurações e insira sua chave de API.')
    st.stop()


if 'messages' not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.markdown(message['content'].replace('$', '\$'))

if prompt := st.chat_input('Digite uma mensagem'):
    st.chat_message('user').markdown(prompt.replace('$', '\$'))
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    with st.chat_message('assistant'):
        msg_placeholder = st.empty()
        response = agent.run(prompt, messages=st.session_state.messages, markdown=True, stream=True)
        full_response = ''
        for chunk in response:
            full_response += chunk.content or ''
            msg_placeholder.markdown(full_response.replace('$', '\$'))
    st.session_state.messages.append({'role': 'assistant', 'content': full_response})
    print(f'chat > {prompt}')
    print(f'chat > {full_response}')
    print(f'chat > {agent.run_response.metrics}')  # type: ignore
