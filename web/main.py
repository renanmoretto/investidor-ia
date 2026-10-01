import logging
from pathlib import Path

import markdown as md
import nh3
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src import settings
from src.chat.agent import get_chat_agent
from src.reports import delete_report, get_report, load_reports
from web import chat_sessions, jobs
from web.chat_stream import follow_lines, start_answer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
)
logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent

app = FastAPI(title='Investidor-IA', on_startup=[settings.ensure_db_dir])
app.mount('/static', StaticFiles(directory=WEB_DIR / 'static'), name='static')

templates = Jinja2Templates(directory=str(WEB_DIR / 'templates'))


def render_markdown(text: str) -> str:
    # the text comes from the LLM and from web search results, so the HTML must be sanitized
    return nh3.clean(md.markdown(text or '', extensions=['tables', 'fenced_code']))


templates.env.filters['markdown'] = render_markdown
templates.env.globals['INVESTORS'] = settings.INVESTORS


def render(request: Request, template: str, **context) -> HTMLResponse:
    context.setdefault('configured', settings.is_configured())
    session = chat_sessions.get(request.cookies.get(chat_sessions.COOKIE_NAME))
    context.setdefault('running_chats', session.running if session else [])
    return templates.TemplateResponse(request, template, context)


@app.get('/', response_class=HTMLResponse)
async def index():
    return RedirectResponse('/chat', status_code=303)


# chat


def _chat_session(request: Request) -> chat_sessions.ChatSession:
    return chat_sessions.get_or_create(request.cookies.get(chat_sessions.COOKIE_NAME))


def _with_cookie(response, session: chat_sessions.ChatSession):
    response.set_cookie(chat_sessions.COOKIE_NAME, session.id, httponly=True, samesite='lax')
    return response


def _check_investor(investor: str):
    if investor not in settings.INVESTORS:
        raise HTTPException(status_code=404, detail='Investidor não encontrado')


@app.get('/api/chat/status')
async def chat_status(request: Request):
    """Investors with an answer in progress, polled by the sidebar."""
    session = chat_sessions.get(request.cookies.get(chat_sessions.COOKIE_NAME))
    return JSONResponse({'running': session.running if session else []})


@app.get('/chat')
async def chat_index(request: Request):
    session = _chat_session(request)
    return _with_cookie(RedirectResponse(f'/chat/{session.last_investor}', status_code=303), session)


@app.get('/chat/{investor}', response_class=HTMLResponse)
async def chat_page(request: Request, investor: str):
    _check_investor(investor)
    session = _chat_session(request)
    session.last_investor = investor
    return _with_cookie(render(request, 'chat.html', session=session, chat=session.chat(investor)), session)


@app.post('/chat/{investor}/new')
async def chat_new(request: Request, investor: str):
    _check_investor(investor)
    session = _chat_session(request)
    session.reset_chat(investor)
    return _with_cookie(RedirectResponse(f'/chat/{investor}', status_code=303), session)


@app.get('/chat/{investor}/messages', response_class=HTMLResponse)
async def chat_messages(request: Request, investor: str):
    """Rendered message list, fetched by the browser after a streamed answer ends."""
    _check_investor(investor)
    session = _chat_session(request)
    return templates.TemplateResponse(request, '_chat_messages.html', {'chat': session.chat(investor)})


@app.post('/chat/{investor}/stop')
async def chat_stop(request: Request, investor: str):
    _check_investor(investor)
    chat = _chat_session(request).chat(investor)
    logger.info('chat stop requested investor=%s streaming=%s', investor, chat.streaming)
    chat.request_stop()
    return JSONResponse({'ok': True})


@app.post('/chat/{investor}/send')
async def chat_send(request: Request, investor: str, message: str = Form(...)):
    """Starts the answer in the background. The browser reads it from /stream."""
    _check_investor(investor)
    session = _chat_session(request)
    chat = session.chat(investor)
    if chat.streaming:
        return JSONResponse({'error': 'Aguarde a resposta atual terminar.'}, status_code=409)
    logger.info('chat message session=%s investor=%s len=%d', session.id, investor, len(message))

    async def run_agent(text: str):
        agent = get_chat_agent(investor=investor, session_id=chat.agent_session_id)
        return await agent.arun(text, stream=True)

    start_answer(chat, message, run_agent)
    return _with_cookie(JSONResponse({'ok': True}, status_code=202), session)


@app.get('/chat/{investor}/stream')
async def chat_stream(request: Request, investor: str):
    """All events of the answer in progress, from its start, then the new ones until it ends.
    A closed connection does not stop the answer."""
    _check_investor(investor)
    chat = _chat_session(request).chat(investor)
    if not chat.streaming:
        return StreamingResponse(iter(()), media_type='application/x-ndjson')
    return StreamingResponse(follow_lines(chat.run), media_type='application/x-ndjson')


# reports


@app.get('/generate', response_class=HTMLResponse)
async def generate_page(request: Request, error: str | None = None):
    return render(request, 'generate.html', error=error)


@app.post('/generate')
async def generate_start(ticker: str = Form(...), investor: str = Form(...)):
    if not settings.is_configured():
        return RedirectResponse('/settings', status_code=303)
    if not ticker.strip():
        return RedirectResponse('/generate?error=Informe+o+ticker+da+ação', status_code=303)
    job = jobs.start_job(ticker, investor)
    return RedirectResponse(f'/generate/{job.id}', status_code=303)


@app.get('/generate/{job_id}', response_class=HTMLResponse)
async def generate_status_page(request: Request, job_id: str):
    job = jobs.get_job(job_id)
    if not job:
        return RedirectResponse('/generate?error=Geração+não+encontrada', status_code=303)
    return render(request, 'generating.html', job=job, steps=jobs.STEPS)


@app.get('/api/jobs/{job_id}')
async def job_status(job_id: str):
    job = jobs.get_job(job_id)
    if not job:
        return JSONResponse({'error': 'not found'}, status_code=404)
    return JSONResponse(job.as_dict())


@app.get('/reports', response_class=HTMLResponse)
async def reports_page(request: Request):
    reports = sorted(load_reports(), key=lambda r: r.generated_at, reverse=True)
    return render(request, 'reports.html', reports=reports)


@app.get('/reports/{report_id}', response_class=HTMLResponse)
async def report_page(request: Request, report_id: str):
    report = get_report(report_id)
    if not report:
        return RedirectResponse('/reports', status_code=303)
    return render(request, 'report.html', report=report)


@app.post('/reports/{report_id}/delete')
async def report_delete(report_id: str):
    await delete_report(report_id)
    return RedirectResponse('/reports', status_code=303)


# settings


@app.get('/settings', response_class=HTMLResponse)
async def settings_page(request: Request, saved: bool = False):
    config = settings.get_llm_config()
    return render(
        request,
        'settings.html',
        config=config,
        api_keys=settings.get_api_keys(),
        provider_options={p: p for p in settings.PROVIDERS},
        saved=saved,
    )


@app.post('/settings')
async def settings_save(
    provider: str = Form(...),
    model: str = Form(''),
    api_key: str = Form(''),
):
    settings.save_api_key(provider, api_key)
    settings.save_model(provider, model)
    return RedirectResponse('/settings?saved=true', status_code=303)
