"""Peças compartilhadas dos testes: banco temporário e uma API do Banco Central falsa (sem internet)."""
from datetime import date, datetime

import httpx
import pytest

from indicadores import load


@pytest.fixture
def engine(tmp_path):
    eng = load.criar_engine(f"sqlite:///{tmp_path / 'teste.db'}")
    load.preparar_banco(eng)
    return eng


class BancoCentralFalso:
    """Responde como a API do SGS a partir de dados em memória e conta as chamadas."""

    def __init__(self, dados: dict[int, list[dict]], falhar: set[int] = frozenset()):
        self.dados = dados  # código da série -> registros {"data": "dd/mm/aaaa", "valor": "..."}
        self.falhar = falhar  # séries que sempre respondem 503
        self.chamadas: list[tuple[int, date, date]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        codigo = int(request.url.path.split("bcdata.sgs.")[1].split("/")[0])
        ini = datetime.strptime(request.url.params["dataInicial"], "%d/%m/%Y").date()
        fim = datetime.strptime(request.url.params["dataFinal"], "%d/%m/%Y").date()
        self.chamadas.append((codigo, ini, fim))
        if codigo in self.falhar:
            return httpx.Response(503)
        registros = [
            r for r in self.dados.get(codigo, [])
            if ini <= datetime.strptime(r["data"], "%d/%m/%Y").date() <= fim
        ]
        return httpx.Response(200, json=registros) if registros else httpx.Response(404)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self))


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch):
    """As novas tentativas esperam alguns segundos; nos testes, não."""
    monkeypatch.setattr("indicadores.extract.time.sleep", lambda s: None)
