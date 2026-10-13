"""API de leitura dos indicadores. Uso: `uv run uvicorn indicadores.api:app --reload`."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.engine import Connection

from . import load
from .config import DATABASE_URL, SERIES, SERIES_POR_SLUG
from .load import execucoes, observacoes, series

# Vira uma lista de escolha na documentação, em vez de um campo de texto livre.
SlugSerie = StrEnum("SlugSerie", [(s.slug, s.slug) for s in SERIES])

DESCRICAO = """
Indicadores econômicos do Brasil coletados diariamente da
[API pública do Banco Central](https://dadosabertos.bcb.gov.br/) e servidos aqui já tratados.

| Indicador | `slug` | Unidade |
| --- | --- | --- |
| Dólar comercial (PTAX, venda) | `dolar` | R$ |
| Meta Selic | `selic` | % ao ano |
| CDI (anualizado) | `cdi` | % ao ano |
| IPCA | `ipca` | % no mês |
| IGP-M | `igpm` | % no mês |

**Como testar:** abra uma rota, clique em **Try it out** e depois em **Execute**.
"""

engine = load.criar_engine(DATABASE_URL)
app = FastAPI(
    title="Indicadores BR",
    description=DESCRICAO,
    version="0.2.0",
    openapi_tags=[
        {"name": "Indicadores", "description": "Valores atuais e históricos de cada indicador."},
        {"name": "Pipeline", "description": "Saúde da coleta: quando rodou, o que entrou e o que falhou."},
    ],
    swagger_ui_parameters={"defaultModelsExpandDepth": -1, "docExpansion": "list"},
)


class Valor(BaseModel):
    data: date = Field(description="Data de referência", examples=["2026-10-13"])
    valor: float = Field(description="Valor na unidade do indicador", examples=[5.0096])


class Indicador(BaseModel):
    slug: SlugSerie = Field(description="Identificador usado nas outras rotas")
    nome: str = Field(examples=["Dólar comercial (PTAX, venda)"])
    unidade: str = Field(examples=["R$"])
    periodicidade: str = Field(description="diaria ou mensal", examples=["diaria"])
    ultimo: Valor | None = Field(description="Valor mais recente; vazio se o pipeline ainda não rodou")


class Historico(BaseModel):
    slug: SlugSerie
    nome: str
    unidade: str
    periodicidade: str
    inicio: date
    fim: date
    total: int = Field(description="Quantidade de valores no período")
    pontos: list[Valor]


class Ultimo(Valor):
    slug: SlugSerie
    unidade: str


class Execucao(BaseModel):
    serie: str
    iniciada_em: datetime
    inicio_periodo: date | None = Field(description="A partir de que data os dados foram pedidos")
    lidos: int = Field(description="Registros recebidos da API do Banco Central")
    gravados: int = Field(description="Registros gravados ou atualizados no banco")
    descartados: int = Field(description="Registros recusados pelas regras de qualidade")
    status: str = Field(examples=["ok"])
    erro: str | None = None


def conexao():
    with engine.connect() as conn:
        yield conn


PAGINA = (Path(__file__).parent / "pagina.html").read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def pagina_inicial():
    """Painel com os valores atuais e o gráfico de cada indicador."""
    return PAGINA


@app.get("/series", tags=["Indicadores"], summary="Listar indicadores com o valor mais recente",
         response_model=list[Indicador])
def listar_series(conn: Connection = Depends(conexao)):
    ultima = (
        select(observacoes.c.serie_codigo, func.max(observacoes.c.data).label("data"))
        .group_by(observacoes.c.serie_codigo)
        .subquery()
    )
    consulta = (
        select(series, observacoes.c.data, observacoes.c.valor)
        .select_from(series)
        .outerjoin(ultima, ultima.c.serie_codigo == series.c.codigo)
        .outerjoin(observacoes, (observacoes.c.serie_codigo == ultima.c.serie_codigo)
                   & (observacoes.c.data == ultima.c.data))
    )
    ordem = {s.slug: i for i, s in enumerate(SERIES)}
    linhas = sorted(conn.execute(consulta), key=lambda r: ordem.get(r.slug, 99))
    return [
        {
            "slug": r.slug, "nome": r.nome, "unidade": r.unidade, "periodicidade": r.periodicidade,
            "ultimo": {"data": r.data, "valor": _num(r.valor)} if r.data else None,
        }
        for r in linhas
    ]


@app.get("/series/{slug}", tags=["Indicadores"], summary="Histórico de um indicador",
         response_model=Historico,
         description="Valores do indicador entre `inicio` e `fim`. Sem datas, devolve o último ano.")
def historico(
    slug: SlugSerie,
    inicio: date | None = Query(None, description="Data inicial (AAAA-MM-DD). Padrão: 1 ano antes do fim",
                                examples=["2026-01-01"]),
    fim: date | None = Query(None, description="Data final (AAAA-MM-DD). Padrão: hoje"),
    conn: Connection = Depends(conexao),
):
    serie = SERIES_POR_SLUG[slug.value]
    fim = fim or date.today()
    inicio = inicio or fim - timedelta(days=365)
    if inicio > fim:
        raise HTTPException(422, "A data inicial precisa ser anterior à data final.")
    consulta = (
        select(observacoes.c.data, observacoes.c.valor)
        .where(observacoes.c.serie_codigo == serie.codigo,
               observacoes.c.data.between(inicio, fim))
        .order_by(observacoes.c.data)
    )
    pontos = [{"data": r.data, "valor": _num(r.valor)} for r in conn.execute(consulta)]
    return {"slug": serie.slug, "nome": serie.nome, "unidade": serie.unidade,
            "periodicidade": serie.periodicidade, "inicio": inicio, "fim": fim,
            "total": len(pontos), "pontos": pontos}


@app.get("/series/{slug}/ultimo", tags=["Indicadores"], summary="Valor mais recente de um indicador",
         response_model=Ultimo)
def ultimo(slug: SlugSerie, conn: Connection = Depends(conexao)):
    serie = SERIES_POR_SLUG[slug.value]
    consulta = (
        select(observacoes.c.data, observacoes.c.valor)
        .where(observacoes.c.serie_codigo == serie.codigo)
        .order_by(observacoes.c.data.desc())
        .limit(1)
    )
    linha = conn.execute(consulta).first()
    if not linha:
        raise HTTPException(404, f"Ainda não há dados de '{serie.slug}'. Rode o pipeline primeiro.")
    return {"slug": serie.slug, "unidade": serie.unidade, "data": linha.data, "valor": _num(linha.valor)}


@app.get("/execucoes", tags=["Pipeline"], summary="Últimas execuções da coleta",
         response_model=list[Execucao])
def ultimas_execucoes(
    limite: int = Query(20, ge=1, le=200, description="Quantas execuções mostrar (1 a 200)"),
    conn: Connection = Depends(conexao),
):
    consulta = (
        select(execucoes, series.c.slug)
        .join(series, series.c.codigo == execucoes.c.serie_codigo)
        .order_by(execucoes.c.id.desc())
        .limit(limite)
    )
    return [
        {"serie": r.slug, "iniciada_em": r.iniciada_em, "inicio_periodo": r.inicio_periodo,
         "lidos": r.lidos, "gravados": r.gravados, "descartados": r.descartados,
         "status": r.status, "erro": r.erro}
        for r in conn.execute(consulta)
    ]


def _num(valor) -> float | None:
    return float(valor) if isinstance(valor, (Decimal, float, int)) else None
