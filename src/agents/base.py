import logging
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


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


def structured_output(response) -> BaseAgentOutput:
    """agno returns None or the raw text, with no error, when the model gives an empty or invalid answer."""
    content = response.content
    if not isinstance(content, BaseAgentOutput):
        logger.error('model returned no valid structured answer content_type=%s', type(content).__name__)
        raise ValueError('O modelo não retornou uma resposta válida. Tente novamente ou use outro modelo.')
    return content
