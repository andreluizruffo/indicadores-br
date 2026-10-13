# Decisões técnicas

Por que o projeto é feito assim. Cada item diz o que foi escolhido, por quê e o que ficou de fora.

## Escopo

**Faz:** coleta 5 indicadores do Banco Central uma vez por dia, guarda o histórico desde 2015 e serve por API e por um painel.

**Não faz (de propósito):** cotação em tempo real, previsão, login de usuário e escrita pela API. A API é só de leitura; quem grava é o pipeline.

## Stack

| Parte | Escolha | Por quê | Alternativa descartada |
| --- | --- | --- | --- |
| Linguagem | Python 3.13 + uv | padrão em engenharia de dados; o uv trava as versões no `uv.lock` e instala em segundos | pip + requirements.txt (sem lock confiável) |
| Requisições | httpx | tem `MockTransport`, que simula a API nos testes sem internet | requests (precisaria de outra biblioteca para simular) |
| Banco | PostgreSQL em produção, SQLite no desenvolvimento | roda local sem instalar nada; o CI prova que funciona no Postgres de verdade | só Postgres (atrapalha quem quer só testar) |
| Acesso ao banco | SQLAlchemy Core, sem ORM | o trabalho é upsert em lote e consultas simples; o ORM não ajudaria e deixaria a carga mais lenta | ORM com classes de modelo |
| API | FastAPI + Pydantic | documentação `/docs` gerada sozinha e validação dos parâmetros | Flask (documentação à mão) |
| Painel | HTML único + Chart.js do CDN | uma tela só não justifica React nem etapa de build | React + Vite |
| Infra | Docker Compose + GitHub Actions | sobe Postgres e API iguais na máquina e no CI | instalar Postgres na mão |

## Dados

- **Valor como `Numeric(18,6)`, não `float`.** Dinheiro e taxa não podem perder casas na gravação. Na resposta JSON ele vira número comum, porque ali é só para exibir.
- **Chave primária `(serie_codigo, data)`.** Uma série tem no máximo um valor por dia. É isso que permite o `ON CONFLICT DO UPDATE`.
- **Upsert em vez de "apagar e inserir".** Rodar de novo não duplica nada, e se o Banco Central corrigir um valor, a correção entra.
- **Lotes de 500 linhas por comando.** A primeira carga tem uns 10 mil registros, e um comando por linha seria lento.
- **Catálogo de séries no código (`config.py`) e espelhado no banco.** Adicionar um indicador é uma linha de código; o banco é atualizado sozinho na próxima execução.

## Coleta

- **Incremental:** pergunta ao banco a última data gravada e pede à API só o que vem depois. `--desde` força uma recarga.
- **Janelas de 5 anos:** a API recusa mais de 10 anos em séries diárias. Cinco deixa margem.
- **3 tentativas com espera de 1 s e 2 s**, só para erro de rede ou 5xx. Um erro 4xx não melhora tentando de novo.
- **Respostas fora do padrão viram regra com teste:** `200` com erro `404` dentro do JSON significa "sem dados"; qualquer outro formato inesperado vira erro claro.
- **Datas futuras são descartadas:** a meta Selic vem preenchida até a próxima reunião do Copom, e isso não é dado observado.
- **Transação por série e erro isolado:** se o IPCA falhar, o dólar grava normal, e a falha fica registrada em `execucoes`.

## Testes

- A API do Banco Central é **simulada**: os testes rodam sem internet, sempre com o mesmo resultado e em segundos.
- O CI tem dois jobs: **testes** (SQLite) e **Docker + Postgres** (coleta dados reais duas vezes e confere a API). O segundo pega o que a simulação não pega: dialeto do Postgres, rede e formato real da resposta.
