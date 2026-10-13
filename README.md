# Indicadores BR

Pipeline de dados em Python que coleta indicadores econômicos da **API pública do Banco Central** (dólar, Selic, CDI, IPCA e IGP-M), trata os dados, grava no **PostgreSQL** e serve tudo por uma **API em FastAPI**.

> 🇺🇸 English summary below.

## O que ele faz

```
API do Banco Central (SGS)  →  extração  →  transformação  →  carga (PostgreSQL)  →  API (FastAPI)
                               janelas      qualidade          upsert idempotente     /series, /execucoes
                               + retry      dos dados          + histórico
```

| Série | Código SGS | Periodicidade |
| --- | --- | --- |
| Dólar comercial (PTAX, venda) | 1 | diária |
| Meta Selic | 432 | diária |
| CDI (anualizado, base 252) | 4389 | diária |
| IPCA | 433 | mensal |
| IGP-M | 189 | mensal |

## Decisões de engenharia

- **Carga incremental:** a primeira execução busca desde 2015; as seguintes pedem à API só o que ainda não está no banco.
- **Idempotência:** gravação com `INSERT ... ON CONFLICT DO UPDATE` em lotes. Rodar duas vezes não duplica nada, e um valor corrigido na fonte é atualizado.
- **Respeito aos limites da fonte:** a API só aceita janelas de até 10 anos em séries diárias; o extrator divide o período em janelas de 5 anos.
- **Resiliência:** novas tentativas com espera crescente em erro de rede ou do servidor; uma série com problema não derruba as outras.
- **Qualidade dos dados:** datas e valores inválidos são descartados com o motivo; **datas futuras são descartadas** (a meta Selic vem preenchida até a próxima reunião do Copom); datas repetidas ficam com o último valor.
- **Particularidades reais da API**, descobertas rodando o pipeline e cobertas por teste: quando não há dado novo, ela às vezes responde `200` com um erro `404` dentro do JSON; nas séries mensais, devolve o último mês mesmo fora do período pedido (a gravação idempotente absorve isso).
- **Observabilidade:** cada execução fica registrada (lidos, gravados, descartados, status e erro) e pode ser consultada em `/execucoes`.
- **Transação por série:** ou grava a série inteira, ou nada.

## API

| Rota | O que retorna |
| --- | --- |
| `GET /series` | catálogo com o valor mais recente de cada série |
| `GET /series/{slug}?inicio=AAAA-MM-DD&fim=AAAA-MM-DD` | histórico (padrão: último ano) |
| `GET /series/{slug}/ultimo` | valor mais recente |
| `GET /execucoes` | saúde do pipeline: últimas execuções |
| `GET /docs` | documentação interativa (Swagger) |

## Como rodar

Com [uv](https://docs.astral.sh/uv/) (sem Docker, usa SQLite local):

```bash
uv sync
uv run indicadores                      # coleta (incremental)
uv run indicadores --desde 2024-01-01   # recarrega a partir de uma data
uv run uvicorn indicadores.api:app      # API em http://localhost:8000/docs
uv run pytest                           # testes
```

Com Docker e PostgreSQL:

```bash
docker compose up -d --build db api
docker compose run --rm pipeline
curl localhost:8000/series
```

## Testes e CI

- **19 testes** com pytest, sem internet: a API do Banco Central é simulada (`httpx.MockTransport`), incluindo falhas, respostas fora do padrão, carga incremental, idempotência e erro isolado por série.
- **GitHub Actions** em todo envio: roda os testes e depois sobe **PostgreSQL + API em Docker**, coleta dados reais, roda de novo para provar a carga incremental e confere as respostas da API.

## Estrutura

```
src/indicadores/
  config.py     séries coletadas e configuração
  extract.py    chamadas à API do Banco Central (janelas, retry, respostas fora do padrão)
  transform.py  regras de qualidade dos dados
  load.py       tabelas, upsert em lote e histórico de execuções (SQLAlchemy)
  pipeline.py   orquestração e linha de comando
  api.py        API de leitura (FastAPI)
tests/          testes com a API do Banco Central simulada
```

---

## 🇺🇸 English summary

A Python data pipeline that pulls Brazilian economic indicators (USD/BRL, Selic, CDI, IPCA, IGP-M) from the Central Bank's public API, validates them, loads them into PostgreSQL with **incremental, idempotent upserts**, and serves them through a **FastAPI** service. It handles the API's real quirks (10-year window limit, `404` errors wrapped in `200` responses, future-dated Selic targets), retries transient failures, isolates per-series errors and logs every run. 19 pytest tests run offline against a mocked API; GitHub Actions runs them and then spins up PostgreSQL + the API in Docker, ingests real data and checks the endpoints.
