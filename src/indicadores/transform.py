"""Transformação: converte os registros brutos da API em dados limpos e confiáveis."""
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class Ponto:
    data: date
    valor: Decimal


@dataclass
class Resultado:
    pontos: list[Ponto]
    descartados: list[str] = field(default_factory=list)  # motivo de cada linha descartada


def transformar(registros: list[dict], hoje: date) -> Resultado:
    """
    Regras de qualidade:
    - data no formato dd/mm/aaaa e valor numérico; o que não for, é descartado com o motivo;
    - datas futuras são descartadas (a meta Selic vem preenchida até a próxima reunião do Copom);
    - datas repetidas ficam com o último valor recebido;
    - resultado ordenado por data.
    """
    por_data: dict[date, Decimal] = {}
    descartados: list[str] = []

    for registro in registros:
        bruto_data, bruto_valor = registro.get("data"), registro.get("valor")
        try:
            dia = datetime.strptime(str(bruto_data), "%d/%m/%Y").date()
        except ValueError:
            descartados.append(f"data inválida: {bruto_data!r}")
            continue
        try:
            valor = Decimal(str(bruto_valor).strip())
            if not valor.is_finite():
                raise InvalidOperation
        except InvalidOperation:
            descartados.append(f"valor inválido em {bruto_data}: {bruto_valor!r}")
            continue
        if dia > hoje:
            descartados.append(f"data futura: {bruto_data}")
            continue
        por_data[dia] = valor

    pontos = [Ponto(dia, valor) for dia, valor in sorted(por_data.items())]
    return Resultado(pontos, descartados)
