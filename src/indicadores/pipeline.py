"""Pipeline: extrai, transforma e carrega cada série. Uso: `uv run indicadores [--desde AAAA-MM-DD]`."""
import argparse
import logging
from datetime import date, timedelta

import httpx
from sqlalchemy.engine import Engine

from . import load
from .config import DATABASE_URL, INICIO_PADRAO, SERIES, SERIES_POR_SLUG, Serie
from .extract import extrair
from .transform import transformar

log = logging.getLogger("indicadores")


def processar_serie(engine: Engine, client: httpx.Client, serie: Serie, hoje: date,
                    desde: date | None = None) -> None:
    """Uma série do começo ao fim. Sem `desde`, busca só o que ainda não está no banco."""
    with engine.connect() as conn:
        ultima = load.ultima_data(conn, serie.codigo)
    inicio = desde or (ultima + timedelta(days=1) if ultima else INICIO_PADRAO)

    if inicio > hoje:
        log.info("%s: já atualizada até %s", serie.slug, ultima)
        return

    try:
        brutos = extrair(client, serie.codigo, inicio, hoje)
        resultado = transformar(brutos, hoje)
        with engine.begin() as conn:  # transação: ou grava tudo, ou nada
            gravados = load.gravar(conn, serie.codigo, resultado.pontos)
            load.registrar_execucao(conn, serie, inicio, lidos=len(brutos), gravados=gravados,
                                    descartados=len(resultado.descartados))
        log.info("%s: %d lidos, %d gravados, %d descartados (desde %s)",
                 serie.slug, len(brutos), gravados, len(resultado.descartados), inicio)
        for motivo in resultado.descartados[:5]:
            log.debug("%s descartado: %s", serie.slug, motivo)
    except Exception as erro:  # uma série com problema não derruba as outras
        log.error("%s: falhou: %s", serie.slug, erro)
        with engine.begin() as conn:
            load.registrar_execucao(conn, serie, inicio, erro=str(erro)[:1000])


def executar(engine: Engine, client: httpx.Client, series: tuple[Serie, ...] = SERIES,
             hoje: date | None = None, desde: date | None = None) -> None:
    load.preparar_banco(engine)
    for serie in series:
        processar_serie(engine, client, serie, hoje or date.today(), desde)


def main() -> None:
    parser = argparse.ArgumentParser(description="Coleta indicadores do Banco Central.")
    parser.add_argument("--desde", type=date.fromisoformat,
                        help="recarrega a partir desta data (AAAA-MM-DD); sem ela, é incremental")
    parser.add_argument("--series", help=f"lista separada por vírgula: {','.join(SERIES_POR_SLUG)}")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # sem uma linha por requisição
    escolhidas = SERIES
    if args.series:
        escolhidas = tuple(SERIES_POR_SLUG[s.strip()] for s in args.series.split(","))

    with httpx.Client(headers={"User-Agent": "indicadores-br/0.1"}) as client:
        executar(load.criar_engine(DATABASE_URL), client, escolhidas, desde=args.desde)


if __name__ == "__main__":
    main()
