from datetime import date
from decimal import Decimal

from indicadores.transform import transformar

HOJE = date(2026, 10, 13)


def test_converte_data_e_valor():
    r = transformar([{"data": "09/10/2026", "valor": "4.9892"}], HOJE)
    assert r.pontos[0].data == date(2026, 10, 9)
    assert r.pontos[0].valor == Decimal("4.9892")
    assert r.descartados == []


def test_descarta_valor_e_data_invalidos_com_motivo():
    r = transformar([
        {"data": "09/10/2026", "valor": ""},
        {"data": "2026-10-09", "valor": "1"},
        {"data": "08/10/2026", "valor": "NaN"},
        {"data": "07/10/2026", "valor": "5.01"},
    ], HOJE)
    assert [p.data for p in r.pontos] == [date(2026, 10, 7)]
    assert len(r.descartados) == 3


def test_descarta_datas_futuras():
    # a meta Selic vem preenchida até a próxima reunião do Copom
    r = transformar([
        {"data": "13/10/2026", "valor": "13.75"},
        {"data": "14/10/2026", "valor": "13.75"},
    ], HOJE)
    assert [p.data for p in r.pontos] == [HOJE]
    assert r.descartados == ["data futura: 14/10/2026"]


def test_data_repetida_fica_com_o_ultimo_valor_e_resultado_ordenado():
    r = transformar([
        {"data": "02/10/2026", "valor": "2"},
        {"data": "01/10/2026", "valor": "1"},
        {"data": "02/10/2026", "valor": "3"},
    ], HOJE)
    assert [(p.data.day, p.valor) for p in r.pontos] == [(1, Decimal("1")), (2, Decimal("3"))]
