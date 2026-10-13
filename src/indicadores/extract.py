"""Extração: busca os dados brutos na API do Banco Central (SGS)."""
import time
from collections.abc import Iterator
from datetime import date, timedelta

import httpx

from .config import BCB_URL

# A API recusa janelas maiores que 10 anos em séries diárias; 5 anos dá folga.
ANOS_POR_JANELA = 5
TENTATIVAS = 3


class ErroExtracao(Exception):
    pass


def janelas(inicio: date, fim: date, anos: int = ANOS_POR_JANELA) -> Iterator[tuple[date, date]]:
    """Divide o período em pedaços de no máximo `anos` anos, sem sobreposição."""
    atual = inicio
    while atual <= fim:
        try:
            limite = atual.replace(year=atual.year + anos) - timedelta(days=1)
        except ValueError:  # 29/02 em ano não bissexto
            limite = atual.replace(year=atual.year + anos, day=28) - timedelta(days=1)
        yield atual, min(limite, fim)
        atual = min(limite, fim) + timedelta(days=1)


def buscar_janela(client: httpx.Client, codigo: int, inicio: date, fim: date) -> list[dict]:
    """Uma chamada à API, com novas tentativas em erro de rede ou do servidor."""
    params = {
        "formato": "json",
        "dataInicial": inicio.strftime("%d/%m/%Y"),
        "dataFinal": fim.strftime("%d/%m/%Y"),
    }
    url = BCB_URL.format(codigo=codigo)
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            resposta = client.get(url, params=params, timeout=30)
        except httpx.TransportError as erro:
            motivo = f"falha de rede: {erro}"
        else:
            if resposta.status_code == 404:
                return []  # a API responde 404 quando não há dados no período
            if resposta.status_code < 500:
                resposta.raise_for_status()
                return _registros(resposta.json(), codigo)
            motivo = f"HTTP {resposta.status_code}"
        if tentativa < TENTATIVAS:
            time.sleep(2 ** (tentativa - 1))  # espera 1s, depois 2s
    raise ErroExtracao(f"série {codigo}, {inicio} a {fim}: {motivo}")


def _registros(corpo, codigo: int) -> list[dict]:
    """
    A API às vezes responde 200 com um erro dentro, por exemplo quando não há dado novo:
    {"erro": {"statusCode": 404, "detail": "... Value(s) not found"}}
    """
    if isinstance(corpo, list):
        return corpo
    erro = corpo.get("erro", {}) if isinstance(corpo, dict) else {}
    if erro.get("statusCode") == 404:
        return []
    raise ErroExtracao(f"série {codigo}: resposta inesperada: {str(corpo)[:200]}")


def extrair(client: httpx.Client, codigo: int, inicio: date, fim: date) -> list[dict]:
    """Todos os registros da série no período, buscando janela por janela."""
    registros: list[dict] = []
    for ini, fi in janelas(inicio, fim):
        registros.extend(buscar_janela(client, codigo, ini, fi))
    return registros
