import logging
import threading
import uuid
from dataclasses import dataclass, field

from src.reports import STEPS, Report, add_report, generate_report

logger = logging.getLogger(__name__)

_STEP_LABELS = dict(STEPS)


@dataclass
class Job:
    id: str
    ticker: str
    investor_name: str
    status: str = 'running'  # running | done | error
    step: str = ''
    error: str = ''
    report_id: str = ''
    done_steps: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            'id': self.id,
            'ticker': self.ticker,
            'investor_name': self.investor_name,
            'status': self.status,
            'step': self.step,
            'step_label': _STEP_LABELS.get(self.step, ''),
            'done_steps': self.done_steps,
            'error': self.error,
            'report_id': self.report_id,
        }


_jobs: dict[str, Job] = {}
_lock = threading.Lock()


def get_job(job_id: str) -> Job | None:
    with _lock:
        return _jobs.get(job_id)


def start_job(ticker: str, investor_name: str) -> Job:
    job = Job(id=uuid.uuid4().hex, ticker=ticker.upper().strip(), investor_name=investor_name)
    with _lock:
        _jobs[job.id] = job

    threading.Thread(target=_run, args=(job,), daemon=True).start()
    logger.info('job started id=%s ticker=%s investor=%s', job.id, job.ticker, job.investor_name)
    return job


def _run(job: Job):
    def on_step(step: str):
        with _lock:
            if job.step:
                job.done_steps.append(job.step)
            job.step = step

    try:
        report: Report = generate_report(job.ticker, job.investor_name, on_step=on_step)
        add_report(report)
        with _lock:
            job.done_steps.append(job.step)
            job.step = ''
            job.status = 'done'
            job.report_id = report.id
        logger.info('job done id=%s report_id=%s', job.id, report.id)
    except Exception as e:
        logger.exception('job failed id=%s ticker=%s', job.id, job.ticker)
        with _lock:
            job.status = 'error'
            job.error = str(e)
