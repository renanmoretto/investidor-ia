# Investidor-IA 

**Investidor-IA** é um projeto open-source em Python que utiliza modelos de linguagem (LLMs) para gerar relatórios de análise de ações no mercado brasileiro, simulando o estilo de investidores renomados como Warren Buffett, Benjamin Graham, Peter Lynch, Luiz Barsi, entre outros. O sistema coleta dados públicos de diversas fontes, processa-os através de agentes especializados e gera relatórios detalhados no estilo do investidor escolhido.

PS: Atualmente o projeto funciona apenas com o Gemini. OpenAI e outros LLMs serão implementados no futuro.

Você pode gerar um api key do Gemini de forma gratuita no site da google:
https://aistudio.google.com/apikey

## Funcionamento

O processo segue o seguinte fluxo:

1. Usuário fornece uma ação (exemplo: `PETR4`, `VALE3`, `ITUB4`)
2. Usuário escolhe um investidor (Buffett, Graham, Lynch, Barsi)
3. O sistema busca na web dados e notícias sobre a ação
4. Vários subagentes processam os documentos:
   - Analista de releases de resultados
   - Analista financeiro
   - Analista de valuation
   - Analista de notícias
5. O agente final (investidor escolhido) recebe os resumos, dados sobre a empresa e gera um relatório completo
6. O relatório é exibido para o usuário com análises detalhadas e recomendações

## Instalação

### Configuração

1. Clone o repositório:
```bash
git clone https://github.com/renanmoretto/investidor-ia.git
cd investidor-ia
```

2. Crie e ative um ambiente virtual (caso não esteja usando o uv):
```bash
python -m venv .venv

# No Windows
.venv\Scripts\activate

# No Linux/Mac
source .venv/bin/activate
```

3. Instale as dependências:
```bash
pip install -e .
```

4. Configure suas chaves de API:
```bash
cp .env.example .env
```
Edite o arquivo `.env` e adicione sua chave de API.
```
GEMINI_API_KEY=your_api_key
```

## Uso

Execute o script principal e siga as instruções:

```bash
python main.py
```

Ou usando o uv
```bash
uv run main.py
```

## Exemplo do relatório (para ITUB4)

![Descrição da imagem](output-example.png)

## Disclaimer

**IMPORTANTE**: Este projeto é EXCLUSIVAMENTE para fins educacionais e de aprendizado. Não tem qualquer intenção de se tornar um produto comercial e, sob nenhuma circunstância, deve ser considerado como uma análise financeira real ou profissional.

As análises geradas por este sistema:
- NÃO constituem recomendações de investimento
- NÃO devem ser utilizadas para tomar decisões financeiras
- NÃO substituem o aconselhamento de profissionais qualificados
- NÃO garantem precisão, completude ou adequação para qualquer propósito específico

O projeto foi desenvolvido como um exercício de programação e aplicação de inteligência artificial, sem qualquer validação por profissionais do mercado financeiro. Os desenvolvedores não se responsabilizam por quaisquer perdas ou danos resultantes do uso destas informações.

Investimentos em renda variável envolvem riscos significativos e podem resultar em perdas patrimoniais. Sempre consulte um profissional financeiro certificado antes de tomar decisões de investimento.

## Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests.

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para mais detalhes.


## TODOs
* ✅ Analistas (release, financeiro e valuation)
* ✅ Warren Buffett
* ✅ Barsi
* ✅ Analista de notícias
* ⬜ Peter Lynch
* ⬜ Analista técnico (price action e gráficos)
* ⬜ OpenAI/Anthropic LLMs
* ⬜ Seleção de modelos (poder selecionar o modelo que quiser)
* ⬜ Analista macro
* ⬜ Mais investidores (Bill Ackman, Charlie Munger, etc)
* ⬜ Streamlit frontend
* ⬜ Visão dos relatórios dos analistas