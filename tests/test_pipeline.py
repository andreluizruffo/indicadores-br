from datetime import date, timedelta

from sqlalchemy import func, select

from indicadores import load
from indicadores.config import SERIES_POR_SLUG
from indicadores.pipeline import executar
from tests.conftest import BancoCentralFalso

DOLAR = SERIES_POR_SLUG["dolar"]
IPCA = SERIES_POR_SLUG["ipca"]


def _diario(inicio: date, dias: int) -> list[dict]:
    return [{"data": (inicio + timedelta(days=i)).strftime("%d/%m/%Y"), "valor": f"5.{i:04d}"}
            for i in range(dias)]


def _contar(engine, codigo: int) -> int:
    with engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(load.observacoes)
                            .where(load.observacoes.c.serie_codigo == codigo)).scalar()


def test_carga_completa_e_rodar_de_novo_nao_duplica(engine):
    bc = BancoCentralFalso({1: _diario(date(2026, 1, 1), 30)})
    executar(engine, bc.client(), (DOLAR,), hoje=date(2026, 1, 30), desde=date(2026, 1, 1))
    executar(engine, bc.client(), (DOLAR,), hoje=date(2026, 1, 30), desde=date(2026, 1, 1))
    assert _contar(engine, 1) == 30


def test_segunda_execucao_e_incremental(engine):
    bc = BancoCentralFalso({1: _diario(date(2026, 1, 1), 40)})
    executar(engine, bc.client(), (DOLAR,), hoje=date(2026, 1, 20), desde=date(2026, 1, 1))
    bc.chamadas.clear()

    executar(engine, bc.client(), (DOLAR,), hoje=date(2026, 2, 9))

    # só pede o que falta: do dia seguinte ao último gravado até hoje
    assert bc.chamadas == [(1, date(2026, 1, 21), date(2026, 2, 9))]
    assert _contar(engine, 1) == 40


def test_serie_com_erro_nao_derruba_as_outras_e_fica_registrada(engine):
    bc = BancoCentralFalso({433: [{"data": "01/09/2026", "valor": "0.82"}]}, falhar={1})
    executar(engine, bc.client(), (DOLAR, IPCA), hoje=date(2026, 10, 13), desde=date(2026, 9, 1))

    assert _contar(engine, 433) == 1
    with engine.connect() as conn:
        status = dict(conn.execute(select(load.execucoes.c.serie_codigo, load.execucoes.c.status)).all())
    assert status == {1: "erro", 433: "ok"}


def test_valor_corrigido_na_fonte_e_atualizado(engine):
    bc = BancoCentralFalso({433: [{"data": "01/09/2026", "valor": "0.80"}]})
    executar(engine, bc.client(), (IPCA,), hoje=date(2026, 10, 13), desde=date(2026, 9, 1))
    bc.dados[433] = [{"data": "01/09/2026", "valor": "0.82"}]
    executar(engine, bc.client(), (IPCA,), hoje=date(2026, 10, 13), desde=date(2026, 9, 1))

    with engine.connect() as conn:
        valor = conn.execute(select(load.observacoes.c.valor)).scalar()
    assert float(valor) == 0.82
