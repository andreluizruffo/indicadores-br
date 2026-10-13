"""API de leitura dos indicadores. Uso: `uv run uvicorn indicadores.api:app --reload`."""
from datetime import date, timedelta
from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.engine import Connection

from . import load
from .config import DATABASE_URL, SERIES_POR_SLUG
from .load import execucoes, observacoes, series

engine = load.criar_engine(DATABASE_URL)
app = FastAPI(
    title="Indicadores BR",
    description="Dólar, Selic, CDI, IPCA e IGP-M coletados da API do Banco Central.",
    version="0.1.0",
)


def conexao():
    with engine.connect() as conn:
        yield conn


def _serie_ou_404(slug: str):
    serie = SERIES_POR_SLUG.get(slug)
    if not serie:
        raise HTTPException(404, f"série '{slug}' não existe; use uma de: {', '.join(SERIES_POR_SLUG)}")
    return serie


@app.get("/")
def raiz():
    return {"api": "Indicadores BR", "docs": "/docs", "series": list(SERIES_POR_SLUG)}


@app.get("/series")
def listar_series(conn: Connection = Depends(conexao)):
    """Catálogo com o valor mais recente de cada série."""
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
        .order_by(series.c.codigo)
    )
    return [
        {
            "slug": r.slug, "nome": r.nome, "unidade": r.unidade, "periodicidade": r.periodicidade,
            "ultimo": {"data": r.data, "valor": _num(r.valor)} if r.data else None,
        }
        for r in conn.execute(consulta)
    ]


@app.get("/series/{slug}")
def historico(
    slug: str,
    inicio: date | None = Query(None, description="AAAA-MM-DD; padrão: 1 ano atrás"),
    fim: date | None = Query(None, description="AAAA-MM-DD; padrão: hoje"),
    conn: Connection = Depends(conexao),
):
    serie = _serie_ou_404(slug)
    fim = fim or date.today()
    inicio = inicio or fim - timedelta(days=365)
    if inicio > fim:
        raise HTTPException(422, "inicio deve ser anterior ao fim")
    consulta = (
        select(observacoes.c.data, observacoes.c.valor)
        .where(observacoes.c.serie_codigo == serie.codigo,
               observacoes.c.data.between(inicio, fim))
        .order_by(observacoes.c.data)
    )
    pontos = [{"data": r.data, "valor": _num(r.valor)} for r in conn.execute(consulta)]
    return {"slug": serie.slug, "nome": serie.nome, "unidade": serie.unidade,
            "inicio": inicio, "fim": fim, "total": len(pontos), "pontos": pontos}


@app.get("/series/{slug}/ultimo")
def ultimo(slug: str, conn: Connection = Depends(conexao)):
    serie = _serie_ou_404(slug)
    consulta = (
        select(observacoes.c.data, observacoes.c.valor)
        .where(observacoes.c.serie_codigo == serie.codigo)
        .order_by(observacoes.c.data.desc())
        .limit(1)
    )
    linha = conn.execute(consulta).first()
    if not linha:
        raise HTTPException(404, f"ainda não há dados de '{slug}'; rode o pipeline")
    return {"slug": serie.slug, "unidade": serie.unidade, "data": linha.data, "valor": _num(linha.valor)}


@app.get("/execucoes")
def ultimas_execucoes(limite: int = Query(20, ge=1, le=200), conn: Connection = Depends(conexao)):
    """Saúde do pipeline: as últimas execuções, com o que entrou e o que falhou."""
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
