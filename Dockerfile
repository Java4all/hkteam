FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md chainlit.md ./
COPY .chainlit ./.chainlit
COPY src ./src
COPY configs ./configs
COPY data ./data

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -e "." \
    && python -c "from chainlit.config import load_config; load_config()"

ENV PYTHONUNBUFFERED=1
ENV API_HOST=0.0.0.0
ENV API_PORT=8080

EXPOSE 8080 7860

CMD ["python", "-m", "uvicorn", "crisis.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
