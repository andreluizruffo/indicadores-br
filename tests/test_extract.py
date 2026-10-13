from datetime import date

import httpx
import pytest

from indicadores.extract import ErroExtracao, buscar_janela, janelas


def test_janelas_cobrem_o_periodo_sem_buracos_nem_sobreposicao():
    partes = list(janelas(date(2015, 1, 1), date(2026, 10, 13), anos=5))
    assert partes[0] == (date(2015, 1, 1), date(2019, 12, 31))
    assert partes[1] == (date(2020, 1, 1), date(2024, 12, 31))
    assert partes[-1] == (date(2025, 1, 1), date(2026, 10, 13))


def test_janela_unica_quando_o_periodo_e_curto():
    assert list(janelas(date(2026, 10, 1), date(2026, 10, 13))) == [(date(2026, 10, 1), date(2026, 10, 13))]


def test_tenta_de_novo_quando_o_servidor_falha():
    respostas = iter([httpx.Response(503), httpx.Response(200, json=[{"data": "01/10/2026", "valor": "1"}])])
    client = httpx.Client(transport=httpx.MockTransport(lambda req: next(respostas)))
    assert buscar_janela(client, 1, date(2026, 10, 1), date(2026, 10, 1)) == [{"data": "01/10/2026", "valor": "1"}]


def test_desiste_depois_de_tres_falhas():
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(500)))
    with pytest.raises(ErroExtracao, match="HTTP 500"):
        buscar_janela(client, 1, date(2026, 10, 1), date(2026, 10, 1))


def test_404_significa_periodo_sem_dados():
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(404)))
    assert buscar_janela(client, 1, date(2026, 10, 1), date(2026, 10, 1)) == []


def test_200_com_erro_404_dentro_tambem_e_periodo_sem_dados():
    # caso real: a API respondeu assim para o CDI num fim de semana
    corpo = {"erro": {"statusCode": 404, "detail": "SGSNegocioException: Value(s) not found"}}
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=corpo)))
    assert buscar_janela(client, 12, date(2026, 10, 10), date(2026, 10, 13)) == []


def test_resposta_em_formato_desconhecido_vira_erro_claro():
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"x": 1})))
    with pytest.raises(ErroExtracao, match="resposta inesperada"):
        buscar_janela(client, 12, date(2026, 10, 10), date(2026, 10, 13))
