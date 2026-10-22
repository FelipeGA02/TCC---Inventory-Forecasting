#!/usr/bin/env bash
# Publica a API e o Job de treino no Cloud Run com o código atual — da raiz do repositório:
#   PROJETO=<id-do-projeto> deploy/publicar.sh
# Precisa de deploy/env.cloudrun.yaml (modelo em deploy/env.cloudrun.example.yaml).
set -euo pipefail
cd "$(dirname "$0")/.."

PROJETO="${PROJETO:?informe PROJETO=<id-do-projeto>}"
REGIAO="${REGIAO:-southamerica-east1}"
ENV_BASE="deploy/env.cloudrun.yaml"
[ -f "$ENV_BASE" ] || { echo "falta $ENV_BASE (copie de deploy/env.cloudrun.example.yaml)"; exit 1; }

JOB="projects/$PROJETO/locations/$REGIAO/jobs/treino"
IMAGEM="$REGIAO-docker.pkg.dev/$PROJETO/verde-perto/api:$(git rev-parse --short HEAD)"
NUMERO="$(gcloud projects describe "$PROJETO" --format='value(projectNumber)')"
CONTA="$NUMERO-compute@developer.gserviceaccount.com"

ENV="$(mktemp)"
trap 'rm -f "$ENV"' EXIT
{ cat "$ENV_BASE"; echo; echo 'TRAINING_RUNNER: "cloud_run_job"'; echo "CLOUD_RUN_JOB: \"$JOB\""; } > "$ENV"

# 1. imagem (Cloud Build: 2.500 min/mês grátis)
gcloud builds submit ia-predictor --project="$PROJETO" --tag="$IMAGEM"

# 2. Job de treino: 4 CPUs e 8 GB só enquanto treina (cota grátis de Jobs)
gcloud run jobs deploy treino --project="$PROJETO" --region="$REGIAO" --image="$IMAGEM" \
  --env-vars-file="$ENV" --command=python --args="-m,backend.scripts.treinar_job" \
  --cpu=4 --memory=8Gi --tasks=1 --max-retries=0 --task-timeout=3h
# a API e o agendamento semanal usam esta conta para iniciar o Job
gcloud run jobs add-iam-policy-binding treino --project="$PROJETO" --region="$REGIAO" \
  --member="serviceAccount:$CONTA" --role=roles/run.invoker >/dev/null

# 3. API: CPU só durante as requisições, desliga sem uso (0 instâncias), no máximo 1
gcloud run deploy api --project="$PROJETO" --region="$REGIAO" --image="$IMAGEM" \
  --env-vars-file="$ENV" --cpu=1 --memory=1Gi --concurrency=40 \
  --min-instances=0 --max-instances=1 --cpu-throttling --no-cpu-boost --timeout=300 \
  --service-account="$CONTA" --allow-unauthenticated

echo
echo "API: $(gcloud run services describe api --project="$PROJETO" --region="$REGIAO" --format='value(status.url)')"
