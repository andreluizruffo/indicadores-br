"""Indicadores BR: pipeline de dados do Banco Central + API."""


def main() -> None:
    from .pipeline import main as pipeline_main

    pipeline_main()
