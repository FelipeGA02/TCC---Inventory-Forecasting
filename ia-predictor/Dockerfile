# API (FastAPI + agendador do treino) para o servidor. Ver deploy/README.md.
# Mesma versão de Python do ambiente local (os pins de requirements.txt são testados nela).
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    TZ=America/Sao_Paulo

# tzdata: datas de `retrain_history` e `processing_log` no horário da loja, como na carga inicial
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# o treino e o upload reaproveitam o código de training_scripts/ (pré-processamento e gerador)
COPY openapi.yaml .
COPY backend backend
COPY training_scripts training_scripts

RUN useradd --create-home app \
    && mkdir -p data models training_scripts/output \
    && chown -R app /app
USER app

EXPOSE 8000
# um processo só: o agendador e o treino rodam dentro da API
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
