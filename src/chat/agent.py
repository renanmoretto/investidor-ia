from textwrap import dedent

from agno.agent import Agent
from agno.models.google.gemini import Gemini
from agno.tools.duckduckgo import DuckDuckGoTools

from src.utils import get_model
from src.chat.tools import StocksTools
from src.settings import get_api_key
from src.agents.investors.barsi import DESCRIPTION as barsi_description
from src.agents.investors.buffett import DESCRIPTION as buffet_description
from src.agents.investors.graham import DESCRIPTION as graham_description


_API_KEY = get_api_key('gemini')


def get_chat_agent(investor: str) -> Agent:
    match investor:
        case 'buffett':
            description = buffet_description
        case 'barsi':
            description = barsi_description
        case 'graham':
            description = graham_description
        case _:
            raise ValueError(f'Investor {investor} not found')

    return Agent(
        model=get_model(),
        tools=[StocksTools(), DuckDuckGoTools()],
        show_tool_calls=False,
        markdown=True,
        description=description,
        instructions=dedent(
            """
            Comece analisando a pergunta do usuário e veja se você pode responder com os dados disponíveis.
            Se precisar de mais dados, use as funções disponíveis. Elas devem ser usadas para obter os dados necessários e responder ao usuário.
            Você tem acesso livre aos dados das ações no Brasil e ao uso das funções disponíveis, se aproveite delas para responder ao usuário.
            Caso você use alguma função disponível, não informe ao usuário que você usou uma função, apenas responda a pergunta.
            """
        ),
    )
