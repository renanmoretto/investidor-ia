import logging
from functools import cache
from textwrap import dedent

from agno.agent import Agent
from agno.db.sqlite import AsyncSqliteDb
from agno.tools.duckduckgo import DuckDuckGoTools

from src.utils import get_model
from src.chat.tools import STOCK_TOOLS
from src.settings import DB_DIR
from src.agents.investors.barsi import SYSTEM_PROMPT as barsi_system_prompt
from src.agents.investors.buffett import SYSTEM_PROMPT as buffet_system_prompt
from src.agents.investors.graham import SYSTEM_PROMPT as graham_system_prompt

logger = logging.getLogger(__name__)


@cache
def _db() -> AsyncSqliteDb:
    # created on first use: AsyncSqliteDb creates the db dir, and that must not happen before settings.ensure_db_dir
    return AsyncSqliteDb(db_file=str(DB_DIR / 'agents_db.db'))


def get_chat_agent(investor: str, session_id: str | None = None) -> Agent:
    match investor:
        case 'buffett':
            system_prompt = buffet_system_prompt
        case 'barsi':
            system_prompt = barsi_system_prompt
        case 'graham':
            system_prompt = graham_system_prompt
        case _:
            raise ValueError(f'Investor {investor} not found')

    logger.info('chat agent created investor=%s session_id=%s', investor, session_id)

    return Agent(
        session_id=session_id,
        model=get_model(temperature=0.5),
        system_message=system_prompt,
        instructions=dedent(
            """
            Comece analisando a pergunta do usuário e veja se você pode responder com os dados disponíveis.
            Se precisar de mais dados, use as funções disponíveis. Elas devem ser usadas para obter os dados necessários e responder ao usuário.
            Você tem acesso livre aos dados das ações no Brasil e ao uso das funções disponíveis, se aproveite delas para responder ao usuário.
            Caso você use alguma função disponível, não informe ao usuário que você usou uma função, apenas responda a pergunta.
            Quando uma evolução no tempo ou uma comparação ficar mais clara de forma visual, use a função criar_grafico.
            """
        ),
        tools=[*STOCK_TOOLS, DuckDuckGoTools()],
        db=_db(),
        enable_agentic_memory=True,
        update_memory_on_run=True,
        add_history_to_context=True,
        num_history_runs=20,
        markdown=True,
    )
