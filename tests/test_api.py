from datetime import date

import pytest
from fastapi.testclient import TestClient

from indicadores.api import app, conexao
from indicadores.config import SERIES_POR_SLUG
from indicadores.pipeline import executar
from tests.conftest import BancoCentralFalso

HOJE = date.today()


@pytest.fixture
def api(engine):
    dolar = [{"data": HOJE.strftime("%d/%m/%Y"), "valor": "5.0096"}]
    executar(engine, BancoCentralFalso({1: dolar}).client(), (SERIES_POR_SLUG["dolar"],),
             hoje=HOJE, desde=HOJE)

    def conexao_de_teste():
        with engine.connect() as conn:
            yield conn

    app.dependency_overrides[conexao] = conexao_de_teste
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_lista_series_com_ultimo_valor(api):
    corpo = api.get("/series").json()
    dolar = next(s for s in corpo if s["slug"] == "dolar")
    assert dolar["ultimo"] == {"data": HOJE.isoformat(), "valor": 5.0096}
    ipca = next(s for s in corpo if s["slug"] == "ipca")
    assert ipca["ultimo"] is None


def test_historico_e_ultimo(api):
    assert api.get("/series/dolar").json()["total"] == 1
    assert api.get("/series/dolar/ultimo").json()["valor"] == 5.0096


def test_erros_claros(api):
    assert api.get("/series/bitcoin").status_code == 404
    assert api.get("/series/ipca/ultimo").status_code == 404
    assert api.get("/series/dolar?inicio=2026-10-10&fim=2026-01-01").status_code == 422


def test_execucoes_mostram_a_saude_do_pipeline(api):
    execucao = api.get("/execucoes").json()[0]
    assert execucao["serie"] == "dolar"
    assert execucao["status"] == "ok"
    assert execucao["gravados"] == 1
