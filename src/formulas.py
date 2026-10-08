import logging
import math

logger = logging.getLogger(__name__)

GRAHAM_MULTIPLIER = 22.5  # P/L máximo de 15 x P/VP máximo de 1,5
BAZIN_MIN_YIELD = 0.06


def _positive(*values) -> bool:
    return all(isinstance(v, (int, float)) and v > 0 for v in values)


def calc_cagr(data: list[dict], name: str, years: int = 5) -> float:
    """
    CAGR entre anos fechados, a linha 'ltm' é ignorada.
    ps: data precisa ser anual e estar em ordem decrescente, do mais novo para o mais antigo
    """
    values = [d[name] for d in data if d.get('data') != 'ltm'][: years + 1]
    if len(values) < 2:
        logger.warning('cagr not calculated name=%s years=%d closed_years_available=%d', name, years, len(values))
        return float('nan')
    if len(values) < years + 1:
        logger.warning('cagr name=%s covers %d years instead of %d', name, len(values) - 1, years)
    return (values[0] / values[-1]) ** (1 / (len(values) - 1)) - 1


def graham_number(lpa: float, vpa: float) -> float | None:
    if not _positive(lpa, vpa):
        return None
    return math.sqrt(GRAHAM_MULTIPLIER * lpa * vpa)


def margin_of_safety(intrinsic_value: float | None, price: float) -> float | None:
    if not _positive(intrinsic_value, price):
        return None
    return 1 - price / intrinsic_value


def bazin_ceiling_price(dividends_per_share: list[float], min_yield: float = BAZIN_MIN_YIELD) -> float | None:
    if not dividends_per_share or not _positive(min_yield):
        return None
    return sum(dividends_per_share) / len(dividends_per_share) / min_yield


def peg_ratio(p_l: float, earnings_growth_pct: float) -> float | None:
    if not _positive(p_l, earnings_growth_pct):
        return None
    return p_l / earnings_growth_pct


def earnings_yield(ebit: float, enterprise_value: float) -> float | None:
    if not isinstance(ebit, (int, float)) or not _positive(enterprise_value):
        return None
    return ebit / enterprise_value
