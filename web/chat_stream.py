import json
import logging
import threading
from collections.abc import Callable, Iterator

from agno.run.response import RunEvent
from pydantic import ValidationError

from src.chat.charts import build_chart_spec
from web.chat_sessions import Chat

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


def _line(event: dict) -> str:
    return json.dumps(event, ensure_ascii=False) + '\n'


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


def stream_answer(chat: Chat, text: str, run: Callable[[str], Iterator]) -> Iterator[str]:
    """Runs the agent and yields one JSON event per line.

    The assistant message is stored in the chat before the first event and updated in place,
    so the partial answer survives a stop or a browser disconnect.
    """
    message = {'role': 'assistant', 'parts': [], 'status': 'streaming'}
    chat.messages.append({'role': 'user', 'content': text})
    chat.messages.append(message)
    # one stop event per answer: a stopped run that is still blocked in a tool call
    # must not be revived, or have its state reset, by the next answer
    stop = threading.Event()
    chat.stop = stop
    chat.streaming = True
    tools: dict[str, dict] = {}
    chunks = None

    try:
        chunks = run(text)
        for chunk in chunks:
            if stop.is_set():
                message['status'] = 'stopped'
                logger.info('chat stopped investor=%s', chat.investor)
                break

            event = getattr(chunk, 'event', '')

            # tool events carry the whole answer so far in `content`; only RunResponse holds a delta
            if event == RunEvent.run_response.value:
                delta = chunk.content
                if isinstance(delta, str) and delta:
                    _append_text(message, delta)
                    yield _line({'type': 'text', 'delta': delta})

            elif event == RunEvent.tool_call_started.value:
                for tool in chunk.tools or []:
                    if tool.tool_call_id in tools:
                        continue
                    part = _tool_part(tool)
                    tools[tool.tool_call_id] = part
                    message['parts'].append(part)
                    logger.info('tool call started name=%s args=%s', part['name'], part['args'])
                    yield _line(part)

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
                    yield _line({**part, 'type': 'tool_done'})
                    if chart:
                        message['parts'].append(chart)
                        yield _line(chart)

            elif event == RunEvent.run_error.value:
                raise RuntimeError(str(chunk.content))

        if message['status'] == 'streaming':
            message['status'] = 'done'
    except Exception as e:
        logger.exception('chat failed investor=%s', chat.investor)
        message['status'] = 'error'
        message['error'] = str(e)
        yield _line({'type': 'error', 'message': str(e)})
    finally:
        # also runs on GeneratorExit, when the browser disconnects mid-answer
        if message['status'] == 'streaming':
            message['status'] = 'stopped'
        for part in tools.values():
            if part['status'] == 'running':
                part['status'] = 'stopped'
        if chunks is not None and hasattr(chunks, 'close'):
            chunks.close()
        if chat.stop is stop:
            chat.streaming = False
        logger.info(
            'chat answer finished investor=%s status=%s parts=%d',
            chat.investor,
            message['status'],
            len(message['parts']),
        )
