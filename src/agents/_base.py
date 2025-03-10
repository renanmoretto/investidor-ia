from typing import Literal

from pydantic import BaseModel


class BaseAgentOutput(BaseModel):
    content: str
    sentiment: Literal['BULLISH', 'BEARISH', 'NEUTRAL']
    confidence: int
