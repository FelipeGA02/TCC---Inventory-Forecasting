#!/usr/bin/env bash
# Preparação do projeto no Google Cloud — rodar UMA vez, da raiz do repositório:
#   PROJETO=<id-do-projeto> deploy/configurar.sh
# Liga as APIs, cria o repositório de imagens (guardando só as 2 últimas, para ficar na
# cota grátis de 0,5 GB) e o agendamento do treino semanal (segunda 02:00).
set -euo pipefail
cd "$(dirname "$0")/.."

PROJETO="${PROJETO:?informe PROJETO=<id-do-projeto>}"
REGIAO="${REGIAO:-southamerica-east1}"

gcloud config set project "$PROJETO"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  cloudbuild.googleapis.com cloudscheduler.googleapis.com

if ! gcloud artifacts repositories describe verde-perto --location="$REGIAO" >/dev/null 2>&1; then
  gcloud artifacts repositories create verde-perto --repository-format=docker \
    --location="$REGIAO" --description="Imagem da API e do Job de treino"
fi
gcloud artifacts repositories set-cleanup-policies verde-perto --location="$REGIAO" \
  --policy=deploy/limpeza-imagens.json --no-dry-run

NUMERO="$(gcloud projects describe "$PROJETO" --format='value(projectNumber)')"
CONTA="$NUMERO-compute@developer.gserviceaccount.com"
if ! gcloud scheduler jobs describe treino-semanal --location="$REGIAO" >/dev/null 2>&1; then
  gcloud scheduler jobs create http treino-semanal --location="$REGIAO" \
    --schedule="0 2 * * 1" --time-zone="America/Sao_Paulo" \
    --uri="https://run.googleapis.com/v2/projects/$PROJETO/locations/$REGIAO/jobs/treino:run" \
    --http-method=POST --oauth-service-account-email="$CONTA"
fi
echo "Pronto. Agora: PROJETO=$PROJETO deploy/publicar.sh"
