FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
# Por padrão sobe a API; o pipeline roda com: docker compose run --rm pipeline
CMD ["uvicorn", "indicadores.api:app", "--host", "0.0.0.0", "--port", "8000"]
