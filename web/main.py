import logging
from pathlib import Path

import markdown as md
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src import settings
from src.chat.agent import get_chat_agent
from src.reports import delete_report, get_report, load_reports
from web import chat_sessions, jobs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
)
logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent

app = FastAPI(title='Investidor-IA', on_startup=[settings.ensure_db_dir])
app.mount('/static', StaticFiles(directory=WEB_DIR / 'static'), name='static')

templates = Jinja2Templates(directory=str(WEB_DIR / 'templates'))
templates.env.filters['markdown'] = lambda text: md.markdown(text or '', extensions=['tables', 'fenced_code'])
templates.env.globals['INVESTORS'] = settings.INVESTORS


def render(request: Request, template: str, **context) -> HTMLResponse:
    context.setdefault('configured', settings.is_configured())
    return templates.TemplateResponse(request, template, context)


@app.get('/', response_class=HTMLResponse)
def index():
    return RedirectResponse('/chat', status_code=303)


# chat


@app.get('/chat', response_class=HTMLResponse)
def chat_page(request: Request):
    session = chat_sessions.get_or_create(request.cookies.get(chat_sessions.COOKIE_NAME))
    response = render(request, 'chat.html', session=session)
    response.set_cookie(chat_sessions.COOKIE_NAME, session.id, httponly=True, samesite='lax')
    return response


@app.post('/chat/new')
def chat_new(request: Request):
    session = chat_sessions.reset(request.cookies.get(chat_sessions.COOKIE_NAME))
    response = RedirectResponse('/chat', status_code=303)
    response.set_cookie(chat_sessions.COOKIE_NAME, session.id, httponly=True, samesite='lax')
    return response


@app.post('/chat/investor')
def chat_set_investor(request: Request, investor: str = Form(...)):
    session = chat_sessions.get_or_create(request.cookies.get(chat_sessions.COOKIE_NAME))
    session.investor = investor
    logger.info('chat investor changed session=%s investor=%s', session.id, investor)
    response = RedirectResponse('/chat', status_code=303)
    response.set_cookie(chat_sessions.COOKIE_NAME, session.id, httponly=True, samesite='lax')
    return response


@app.get('/chat/messages', response_class=HTMLResponse)
def chat_messages(request: Request):
    """Rendered message list, fetched by the browser after a streamed answer ends."""
    session = chat_sessions.get_or_create(request.cookies.get(chat_sessions.COOKIE_NAME))
    return templates.TemplateResponse(request, '_chat_messages.html', {'session': session})


@app.post('/chat/send')
def chat_send(request: Request, message: str = Form(...)):
    session = chat_sessions.get_or_create(request.cookies.get(chat_sessions.COOKIE_NAME))
    session.messages.append({'role': 'user', 'content': message})
    logger.info('chat message session=%s investor=%s len=%d', session.id, session.investor, len(message))

    def stream():
        full_response = ''
        try:
            agent = get_chat_agent(investor=session.investor, session_id=session.id)
            for chunk in agent.run(message, stream=True):
                content = getattr(chunk, 'content', None) or ''
                if not isinstance(content, str):
                    continue
                full_response += content
                yield content
        except Exception as e:
            logger.exception('chat failed session=%s', session.id)
            error = f'\n\n**Erro:** {e}'
            full_response += error
            yield error
        session.messages.append({'role': 'assistant', 'content': full_response})
        logger.info('chat answered session=%s len=%d', session.id, len(full_response))

    response = StreamingResponse(stream(), media_type='text/plain; charset=utf-8')
    response.set_cookie(chat_sessions.COOKIE_NAME, session.id, httponly=True, samesite='lax')
    return response


# reports


@app.get('/generate', response_class=HTMLResponse)
def generate_page(request: Request, error: str | None = None):
    return render(request, 'generate.html', error=error)


@app.post('/generate')
def generate_start(ticker: str = Form(...), investor: str = Form(...)):
    if not settings.is_configured():
        return RedirectResponse('/settings', status_code=303)
    if not ticker.strip():
        return RedirectResponse('/generate?error=Informe+o+ticker+da+ação', status_code=303)
    job = jobs.start_job(ticker, investor)
    return RedirectResponse(f'/generate/{job.id}', status_code=303)


@app.get('/generate/{job_id}', response_class=HTMLResponse)
def generate_status_page(request: Request, job_id: str):
    job = jobs.get_job(job_id)
    if not job:
        return RedirectResponse('/generate?error=Geração+não+encontrada', status_code=303)
    return render(request, 'generating.html', job=job, steps=jobs.STEPS)


@app.get('/api/jobs/{job_id}')
def job_status(job_id: str):
    job = jobs.get_job(job_id)
    if not job:
        return JSONResponse({'error': 'not found'}, status_code=404)
    return JSONResponse(job.as_dict())


@app.get('/reports', response_class=HTMLResponse)
def reports_page(request: Request):
    reports = sorted(load_reports(), key=lambda r: r.generated_at, reverse=True)
    return render(request, 'reports.html', reports=reports)


@app.get('/reports/{report_id}', response_class=HTMLResponse)
def report_page(request: Request, report_id: str):
    report = get_report(report_id)
    if not report:
        return RedirectResponse('/reports', status_code=303)
    return render(request, 'report.html', report=report)


@app.post('/reports/{report_id}/delete')
def report_delete(report_id: str):
    delete_report(report_id)
    return RedirectResponse('/reports', status_code=303)


# settings


@app.get('/settings', response_class=HTMLResponse)
def settings_page(request: Request, saved: bool = False):
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
def settings_save(
    provider: str = Form(...),
    model: str = Form(...),
    google_key: str = Form(''),
    openai_key: str = Form(''),
    openrouter_key: str = Form(''),
):
    settings.save_api_keys({'GOOGLE': google_key, 'OPENAI': openai_key, 'OPENROUTER': openrouter_key})
    settings.save_model(provider, model)
    return RedirectResponse('/settings?saved=true', status_code=303)
