import asyncio

from pydantic_ai import Agent
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool

from src.agents.base import BaseAgentOutput

from pydantic import BaseModel
from typing import Literal


_system_prompt = """
Você é um analista especializado em pesquisar e analisar notícias sobre empresas listadas na B3.
Sua tarefa é buscar e sintetizar as notícias mais relevantes sobre a empresa analisada, focando em:

## OBJETIVOS DA ANÁLISE
1. Identificar eventos significativos recentes que possam impactar a empresa
2. Detectar mudanças estratégicas, aquisições, parcerias ou novos projetos
3. Avaliar a percepção do mercado e da mídia sobre a empresa
4. Monitorar riscos e oportunidades mencionados nas notícias
5. Acompanhar declarações importantes da administração

## ESTRUTURA DO SEU RESUMO
Organize sua resposta em formato markdown seguindo esta estrutura:

### 1. PRINCIPAIS MANCHETES
- Liste as 3-5 notícias mais impactantes encontradas
- Inclua a data e fonte de cada notícia

### 2. EVENTOS CORPORATIVOS
- Mudanças na administração
- Fusões, aquisições ou desinvestimentos
- Novos projetos ou investimentos significativos

### 3. DESEMPENHO E MERCADO
- Notícias sobre resultados financeiros
- Análises de mercado e recomendações de analistas
- Mudanças no setor que afetam a empresa

### 4. RISCOS E CONTROVÉRSIAS
- Processos judiciais relevantes
- Investigações ou denúncias
- Riscos regulatórios ou setoriais

### 5. CONCLUSÃO
- Avaliação do sentimento geral das notícias
- Impacto potencial no curto e médio prazo

## DIRETRIZES IMPORTANTES
- Priorize fontes confiáveis e especializadas
- Mantenha objetividade na análise
- Destaque fatos concretos, não especulações
- Indique claramente a temporalidade das notícias
- Foque em conteúdo relevante para investidores
"""


agent = Agent(
    model='google-gla:gemini-1.5-flash-8b',
    tools=[duckduckgo_search_tool()],
    system_prompt=_system_prompt,
    result_type=BaseAgentOutput,
    retries=1,
)


def analyze(ticker: str, company_name: str) -> BaseAgentOutput:
    async def _analyze():
        r = await agent.run(f'Pesquise notícias sobre a empresa {company_name} ({ticker}).')
        return r.data

    if asyncio.get_event_loop().is_running():
        return asyncio.ensure_future(_analyze())
    else:
        return asyncio.run(_analyze())
