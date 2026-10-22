#!/usr/bin/env bash
# Atualiza a API no servidor com a main do GitHub. Rodar de dentro de deploy/: ./atualizar.sh
# Um treino em andamento é interrompido pelo restart; o agendador refaz no próximo gatilho.
set -euo pipefail
cd "$(dirname "$0")"
git pull --ff-only origin main
docker compose up -d --build
docker image prune -f
docker compose ps
