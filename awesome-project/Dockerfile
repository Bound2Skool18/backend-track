FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev --no-install-project

COPY main.py repository.py ./

EXPOSE 8000

CMD ["/app/.venv/bin/fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
