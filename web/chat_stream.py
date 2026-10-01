import asyncio
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable

from agno.run.response import RunEvent
from pydantic import ValidationError

from src.chat.charts import build_chart_spec
from web.chat_sessions import Chat, Run

logger = logging.getLogger(__name__)

CHART_TOOL = 'criar_grafico'
RESULT_PREVIEW_CHARS = 1500

TOOL_LABELS = {
    'detalhes': 'Detalhes da ação',
    'multiplos': 'Múltiplos',
    'dados_financeiros': 'Dados financeiros',
    'dividendos': 'Dividendos',
    'criar_grafico': 'Gráfico',
    'duckduckgo_search': 'Busca na web',
    'duckduckgo_news': 'Busca de notícias',
}


def _append_text(message: dict, delta: str):
    parts = message['parts']
    if parts and parts[-1]['type'] == 'text':
        parts[-1]['content'] += delta
    else:
        parts.append({'type': 'text', 'content': delta})


def _args_summary(args: dict) -> str:
    values = [str(v) for v in args.values() if isinstance(v, str | int | float) and not isinstance(v, bool)]
    return ' · '.join(values)[:80]


def _tool_part(tool) -> dict:
    name = tool.tool_name or ''
    args = tool.tool_args or {}
    return {
        'type': 'tool',
        'id': tool.tool_call_id or '',
        'name': name,
        'label': TOOL_LABELS.get(name, name),
        'summary': _args_summary(args),
        'args': json.dumps(args, ensure_ascii=False, indent=2),
        'status': 'running',
        'result': '',
    }


def _chart_part(tool) -> dict | None:
    try:
        return {'type': 'chart', 'spec': build_chart_spec(**(tool.tool_args or {}))}
    except (ValidationError, TypeError) as e:
        logger.warning('chart spec invalid tool_call_id=%s error=%s', tool.tool_call_id, e)
        return None


def start_answer(chat: Chat, text: str, run_agent: Callable[[str], Awaitable[AsyncIterator]]) -> Run:
    """Starts the answer as a background task. The assistant message is stored in the chat
    at once and updated in place, so the page can show the partial answer at any time."""
    message = {'role': 'assistant', 'parts': [], 'status': 'streaming'}
    chat.messages.append({'role': 'user', 'content': text})
    chat.messages.append(message)
    run = Run()
    chat.run = run
    run.task = asyncio.create_task(_answer(chat, run, message, text, run_agent))
    return run


async def follow_lines(run: Run) -> AsyncIterator[str]:
    async for event in run.follow():
        yield json.dumps(event, ensure_ascii=False) + '\n'


async def _answer(chat: Chat, run: Run, message: dict, text: str, run_agent: Callable[[str], Awaitable[AsyncIterator]]):
    tools: dict[str, dict] = {}
    try:
        async for chunk in await run_agent(text):
            event = getattr(chunk, 'event', '')

            # tool events carry the whole answer so far in `content`; only RunResponse holds a delta
            if event == RunEvent.run_response.value:
                delta = chunk.content
                if isinstance(delta, str) and delta:
                    _append_text(message, delta)
                    run.publish({'type': 'text', 'delta': delta})

            elif event == RunEvent.tool_call_started.value:
                for tool in chunk.tools or []:
                    if tool.tool_call_id in tools:
                        continue
                    part = _tool_part(tool)
                    tools[tool.tool_call_id] = part
                    message['parts'].append(part)
                    logger.info('tool call started name=%s args=%s', part['name'], part['args'])
                    run.publish(dict(part))

            elif event == RunEvent.tool_call_completed.value:
                for tool in chunk.tools or []:
                    part = tools.get(tool.tool_call_id)
                    if not part or part['status'] != 'running' or tool.result is None:
                        continue
                    part['result'] = str(tool.result)[:RESULT_PREVIEW_CHARS]
                    part['status'] = 'error' if tool.tool_call_error else 'done'

                    chart = None
                    if part['name'] == CHART_TOOL and part['status'] == 'done':
                        chart = _chart_part(tool)
                        if not chart:
                            part['status'] = 'error'

                    logger.info('tool call completed name=%s status=%s', part['name'], part['status'])
                    run.publish({**part, 'type': 'tool_done'})
                    if chart:
                        message['parts'].append(chart)
                        run.publish(chart)

            elif event == RunEvent.run_error.value:
                raise RuntimeError(str(chunk.content))

        message['status'] = 'done'
    except asyncio.CancelledError:
        message['status'] = 'stopped'
    except Exception as e:
        logger.exception('chat failed investor=%s', chat.investor)
        message['status'] = 'error'
        message['error'] = str(e)
        run.publish({'type': 'error', 'message': str(e)})
    finally:
        for part in tools.values():
            if part['status'] == 'running':
                part['status'] = 'stopped'
        run.finish()
        logger.info(
            'chat answer finished investor=%s status=%s parts=%d',
            chat.investor,
            message['status'],
            len(message['parts']),
        )
