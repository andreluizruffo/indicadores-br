"""Carga: grava no banco (PostgreSQL em produção, SQLite no desenvolvimento)."""
from datetime import date, datetime, timezone

from sqlalchemy import (
    Column, Date, DateTime, ForeignKey, Integer, MetaData, Numeric, String, Table, Text,
    create_engine, func, select,
)
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine import Connection, Engine

from .config import SERIES, Serie
from .transform import Ponto

metadata = MetaData()

series = Table(
    "series", metadata,
    Column("codigo", Integer, primary_key=True),
    Column("slug", String(30), unique=True, nullable=False),
    Column("nome", String(100), nullable=False),
    Column("unidade", String(20), nullable=False),
    Column("periodicidade", String(10), nullable=False),
)

observacoes = Table(
    "observacoes", metadata,
    Column("serie_codigo", Integer, ForeignKey("series.codigo"), primary_key=True),
    Column("data", Date, primary_key=True),
    Column("valor", Numeric(18, 6), nullable=False),
)

# Histórico de cada execução: dá para saber quando rodou, o que entrou e o que falhou.
execucoes = Table(
    "execucoes", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("serie_codigo", Integer, ForeignKey("series.codigo"), nullable=False),
    Column("iniciada_em", DateTime(timezone=True), nullable=False),
    Column("inicio_periodo", Date),
    Column("lidos", Integer, nullable=False, default=0),
    Column("gravados", Integer, nullable=False, default=0),
    Column("descartados", Integer, nullable=False, default=0),
    Column("status", String(10), nullable=False),  # "ok" ou "erro"
    Column("erro", Text),
)


def criar_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


def preparar_banco(engine: Engine) -> None:
    """Cria as tabelas (se não existirem) e registra o catálogo de séries."""
    metadata.create_all(engine)
    with engine.begin() as conn:
        for s in SERIES:
            _upsert(conn, series, ["codigo"], {
                "codigo": s.codigo, "slug": s.slug, "nome": s.nome,
                "unidade": s.unidade, "periodicidade": s.periodicidade,
            })


def ultima_data(conn: Connection, codigo: int) -> date | None:
    consulta = select(func.max(observacoes.c.data)).where(observacoes.c.serie_codigo == codigo)
    return conn.execute(consulta).scalar()


LOTE = 500  # linhas por comando INSERT


def gravar(conn: Connection, codigo: int, pontos: list[Ponto]) -> int:
    """Upsert em lotes: rodar duas vezes com os mesmos dados não duplica nada (idempotente)."""
    linhas = [{"serie_codigo": codigo, "data": p.data, "valor": p.valor} for p in pontos]
    for i in range(0, len(linhas), LOTE):
        _upsert(conn, observacoes, ["serie_codigo", "data"], linhas[i:i + LOTE])
    return len(linhas)


def registrar_execucao(conn: Connection, serie: Serie, inicio_periodo: date | None, *,
                       lidos: int = 0, gravados: int = 0, descartados: int = 0,
                       erro: str | None = None) -> None:
    conn.execute(execucoes.insert().values(
        serie_codigo=serie.codigo,
        iniciada_em=datetime.now(timezone.utc),
        inicio_periodo=inicio_periodo,
        lidos=lidos, gravados=gravados, descartados=descartados,
        status="erro" if erro else "ok", erro=erro,
    ))


def _upsert(conn: Connection, tabela: Table, chave: list[str], linhas: dict | list[dict]) -> None:
    """INSERT ... ON CONFLICT DO UPDATE, no dialeto do banco em uso."""
    linhas = [linhas] if isinstance(linhas, dict) else linhas
    if not linhas:
        return
    dialeto = postgresql if conn.dialect.name == "postgresql" else sqlite
    comando = dialeto.insert(tabela).values(linhas)
    # "excluded" = a linha que tentou entrar; em conflito, os campos não-chave são atualizados
    atualizar = {c: comando.excluded[c] for c in linhas[0] if c not in chave}
    conn.execute(comando.on_conflict_do_update(index_elements=chave, set_=atualizar))
