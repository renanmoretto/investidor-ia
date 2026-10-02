import datetime
import logging
import uuid

from pydantic import BaseModel, Field

from src.agents.analysts import earnings_release, financial, news, valuation
from src.agents.investors import barsi, buffett, graham
from src import db
from src.data import stocks
from src.settings import INVESTORS

logger = logging.getLogger(__name__)

_INVESTOR_MODULES = {
    'buffett': buffett,
    'graham': graham,
    'barsi': barsi,
}

STEPS = [
    ('earnings_release', 'Analisando earnings release...'),
    ('financial', 'Analisando dados financeiros...'),
    ('valuation', 'Analisando valuation...'),
    ('news', 'Analisando notícias...'),
    ('investor', 'Gerando relatório final...'),
]


class Report(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    ticker: str
    investor_name: str
    generated_at: datetime.datetime
    data: dict

    @property
    def investor_label(self) -> str:
        return INVESTORS.get(self.investor_name, self.investor_name)

    @property
    def label(self) -> str:
        return f'{self.ticker} - {self.investor_label} - {self.generated_at.strftime("%d/%m/%Y %H:%M")}'


def load_reports() -> list[Report]:
    """All reports, newest first."""
    return [Report(**report) for report in db.list_reports()]


def get_report(report_id: str) -> Report | None:
    report = db.get_report(report_id)
    return Report(**report) if report else None


async def add_report(report: Report):
    db.insert_report(report.model_dump(mode='json'))
    logger.info('report saved id=%s ticker=%s', report.id, report.ticker)


async def delete_report(report_id: str) -> bool:
    if not db.delete_report(report_id):
        logger.warning('report not found for deletion id=%s', report_id)
        return False
    logger.info('report deleted id=%s', report_id)
    return True


async def generate_report(ticker: str, investor_name: str, on_step=None) -> Report:
    """Runs the analyst pipeline and the final investor analysis.

    on_step is called with each step key before it runs, so the caller can report progress.
    """
    if investor_name not in _INVESTOR_MODULES:
        raise ValueError(f'Investidor {investor_name} não encontrado')

    ticker = ticker.upper().strip()
    logger.info('generating report ticker=%s investor=%s', ticker, investor_name)

    await stocks.details(ticker)  # raises ValueError if the ticker does not exist

    def step(key: str):
        logger.info('report step ticker=%s step=%s', ticker, key)
        if on_step:
            on_step(key)

    step('earnings_release')
    earnings_release_analysis = await earnings_release.analyze(ticker)

    step('financial')
    financial_analysis = await financial.analyze(ticker)

    step('valuation')
    valuation_analysis = await valuation.analyze(ticker)

    step('news')
    news_analysis = await news.analyze(ticker=ticker)

    step('investor')
    investor_analysis = await _INVESTOR_MODULES[investor_name].analyze(
        ticker=ticker,
        earnings_release_analysis=earnings_release_analysis,
        financial_analysis=financial_analysis,
        valuation_analysis=valuation_analysis,
        news_analysis=news_analysis,
    )

    report = Report(
        ticker=ticker,
        investor_name=investor_name,
        generated_at=datetime.datetime.now(),
        data={
            'analysts': {
                'earnings_release': earnings_release_analysis.model_dump(),
                'financial': financial_analysis.model_dump(),
                'valuation': valuation_analysis.model_dump(),
                'news': news_analysis.model_dump(),
            },
            'investor': investor_analysis.model_dump(),
        },
    )
    logger.info('report generated ticker=%s investor=%s', ticker, investor_name)
    return report
