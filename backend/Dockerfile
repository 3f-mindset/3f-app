FROM ghcr.io/astral-sh/uv:0.11.17 AS uv
FROM python:3.12-slim-bookworm

COPY --from=uv /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra dev --no-install-project

COPY src ./src
COPY tests ./tests

EXPOSE 8000

CMD ["uv", "run", "--frozen", "--extra", "dev", "uvicorn", "threef.app:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000", "--reload"]
