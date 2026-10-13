"""Configuração: quais séries do Banco Central o pipeline coleta e onde fica o banco."""
import os
from dataclasses import dataclass
from datetime import date
from typing import Literal

Periodicidade = Literal["diaria", "mensal"]


@dataclass(frozen=True)
class Serie:
    codigo: int  # código da série no SGS (Sistema Gerenciador de Séries do Banco Central)
    slug: str  # nome curto usado na API
    nome: str
    unidade: str
    periodicidade: Periodicidade


SERIES: tuple[Serie, ...] = (
    Serie(1, "dolar", "Dólar comercial (PTAX, venda)", "R$", "diaria"),
    Serie(432, "selic", "Meta Selic", "% a.a.", "diaria"),
    Serie(4389, "cdi", "CDI (anualizado)", "% a.a.", "diaria"),
    Serie(433, "ipca", "IPCA", "% no mês", "mensal"),
    Serie(189, "igpm", "IGP-M", "% no mês", "mensal"),
)

SERIES_POR_SLUG = {s.slug: s for s in SERIES}

# Primeira carga começa aqui; as próximas são incrementais (só o que falta).
INICIO_PADRAO = date(2015, 1, 1)

# Sem variável de ambiente, usa um SQLite local (bom para desenvolver e testar).
# Em produção: postgresql+psycopg://usuario:senha@host:5432/banco
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///indicadores.db")

BCB_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
