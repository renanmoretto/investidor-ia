from typing import Literal

from pydantic import BaseModel, Field


class BaseAgentOutput(BaseModel):
    content: str = Field(
        ...,
        description='Conteúdo markdown inteiro da análise, incluindo todos os pontos relevantes.',
    )
    sentiment: Literal['BULLISH', 'BEARISH', 'NEUTRAL'] = Field(
        ...,
        description='Sentimento geral da análise, baseado na interpretação do conteúdo.',
    )
    confidence: int = Field(
        ...,
        description='Um valor entre 0 e 100 que representa a confiança na análise realizada.',
    )
