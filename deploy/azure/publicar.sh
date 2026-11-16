#!/usr/bin/env bash
# Publica a API no Azure Container Apps e o job do treino (deploy/azure/README.md).
# Rode da raiz do repositório, no Git Bash, depois de `az login` com a conta do Azure for Students:
#     bash deploy/azure/publicar.sh
# Na 1ª vez cria tudo; nas seguintes, só publica a imagem nova (código da `HEAD` local).
set -euo pipefail

# Git Bash: caminho no formato C:/... (com MSYS_NO_PATHCONV, git e az não entendem /c/...)
RAIZ="$(cd "$(dirname "$0")/../.." && { pwd -W 2>/dev/null || pwd; })"
ENV_FILE="$RAIZ/deploy/azure/.env.azure"
[ -f "$ENV_FILE" ] || { echo "Falta $ENV_FILE (copie de deploy/azure/env.azure.example)"; exit 1; }
set -a; . "$ENV_FILE"; set +a
for v in DATABASE_URL JWT_SECRET_KEY ADMIN_EMAIL ADMIN_PASSWORD VIEWER_EMAIL VIEWER_PASSWORD CORS_ORIGINS; do
  [ -n "${!v:-}" ] || { echo "Falta $v em $ENV_FILE"; exit 1; }
done

LOC="${AZ_LOCATION:-brazilsouth}"
RG="${AZ_RESOURCE_GROUP:-verde-perto}"
SUB_ID="$(az account show --query id -o tsv)"
ACR="${AZ_ACR:-verdeperto${SUB_ID:0:8}}"; ACR="${ACR//-/}"
AMBIENTE=verde-perto-env
API=verde-perto-api
JOB=verde-perto-treino
WORKERS=4                       # = vCPU do job; a API registra o mesmo valor na configuração do treino
COMMIT="$(git -C "$RAIZ" rev-parse --short=12 HEAD)"
IMAGEM="$ACR.azurecr.io/verde-perto-api:$COMMIT"
JOB_ID="/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.App/jobs/$JOB"
export MSYS_NO_PATHCONV=1       # Git Bash: não converter /subscriptions/... em caminho do Windows

echo ">> assinatura: $(az account show --query name -o tsv) · região $LOC · grupo $RG · commit $COMMIT"
[ -z "$(git -C "$RAIZ" status --porcelain -- ia-predictor)" ] || echo "!! ia-predictor/ tem mudanças não commitadas: vão na imagem, com o commit $COMMIT"

az extension add --name containerapp --upgrade --only-show-errors
for p in Microsoft.App Microsoft.OperationalInsights Microsoft.ContainerRegistry Microsoft.Storage; do
  az provider register --namespace "$p" --wait --only-show-errors
done

az group create -n "$RG" -l "$LOC" -o none
az acr show -n "$ACR" -o none 2>/dev/null || az acr create -n "$ACR" -g "$RG" -l "$LOC" --sku Basic --admin-enabled true -o none
ACR_USER="$(az acr credential show -n "$ACR" --query username -o tsv)"
ACR_PASS="$(az acr credential show -n "$ACR" --query 'passwords[0].value' -o tsv)"

az containerapp env show -n "$AMBIENTE" -g "$RG" -o none 2>/dev/null \
  || az containerapp env create -n "$AMBIENTE" -g "$RG" -l "$LOC" --environment-mode WorkloadProfiles -o none  # Express não aceita jobs
AMBIENTE_ID="$(az containerapp env show -n "$AMBIENTE" -g "$RG" --query id -o tsv)"

# sem `az acr build`: ACR Tasks é bloqueado no Azure for Students (build_imagem.sh usa o kaniko)
echo ">> build da imagem no Azure (sem Docker local; ~10 min)"
if [ -n "$(az acr repository show-tags -n "$ACR" --repository verde-perto-api --query "[?@=='$COMMIT']" -o tsv 2>/dev/null)" ] \
   && [ -z "$(git -C "$RAIZ" status --porcelain -- ia-predictor)" ]; then
  echo "   imagem $COMMIT já existe no registro"
else
  RAIZ="$RAIZ" RG="$RG" LOC="$LOC" ACR="$ACR" ACR_USER="$ACR_USER" ACR_PASS="$ACR_PASS" \
    AMBIENTE_ID="$AMBIENTE_ID" COMMIT="$COMMIT" IMAGEM="$IMAGEM" bash "$RAIZ/deploy/azure/build_imagem.sh"
fi

# Configuração da previsão igual na API e no job (a API registra a receita no disparo; o job treina)
COMUM=(TZ=America/Sao_Paulo "TRAINING_WORKERS=$WORKERS")

echo ">> job do treino ($WORKERS vCPU, 8 GiB, só liga pelo botão)"
if az containerapp job show -n "$JOB" -g "$RG" -o none 2>/dev/null; then
  az containerapp job secret set -n "$JOB" -g "$RG" --secrets "database-url=$DATABASE_URL" -o none
  az containerapp job update -n "$JOB" -g "$RG" --image "$IMAGEM" -o none
else
  # por YAML: o comando tem argumentos com "-" que a linha de comando do az não aceita
  YAML="$(mktemp)"; YAML="$(cygpath -m "$YAML" 2>/dev/null || echo "$YAML")"; trap 'rm -f "$YAML"' EXIT
  cat > "$YAML" <<EOF
location: $LOC
properties:
  environmentId: $AMBIENTE_ID
  configuration:
    triggerType: Manual
    replicaTimeout: 14400
    replicaRetryLimit: 0
    manualTriggerConfig: {parallelism: 1, replicaCompletionCount: 1}
    registries:
      - {server: $ACR.azurecr.io, username: $ACR_USER, passwordSecretRef: acr-password}
    secrets:
      - {name: acr-password, value: '$ACR_PASS'}
      - {name: database-url, value: '$DATABASE_URL'}
  template:
    containers:
      - name: treino
        image: $IMAGEM
        command: [python, -m, backend.scripts.treinar_previsoes, --pendente]
        resources: {cpu: $WORKERS, memory: 8Gi}
        env:
          - {name: DATABASE_URL, secretRef: database-url}
          - {name: TZ, value: America/Sao_Paulo}
          - {name: TRAINING_WORKERS, value: '$WORKERS'}
EOF
  az containerapp job create -n "$JOB" -g "$RG" --yaml "$YAML" -o none
fi

echo ">> API (0,5 vCPU, 1 GiB, sempre ligada, 1 réplica)"
SEGREDOS=("database-url=$DATABASE_URL" "jwt-secret=$JWT_SECRET_KEY"
          "admin-password=$ADMIN_PASSWORD" "viewer-password=$VIEWER_PASSWORD")
VARS=(DATABASE_URL=secretref:database-url JWT_SECRET_KEY=secretref:jwt-secret
      "ADMIN_EMAIL=$ADMIN_EMAIL" ADMIN_PASSWORD=secretref:admin-password
      "VIEWER_EMAIL=$VIEWER_EMAIL" VIEWER_PASSWORD=secretref:viewer-password
      "CORS_ORIGINS=$CORS_ORIGINS" DOCS_ENABLED=false
      TRAINING_RUNNER=azure_job "AZURE_TRAINING_JOB_ID=$JOB_ID" "${COMUM[@]}")
if az containerapp show -n "$API" -g "$RG" -o none 2>/dev/null; then
  az containerapp secret set -n "$API" -g "$RG" --secrets "${SEGREDOS[@]}" -o none
  az containerapp update -n "$API" -g "$RG" --image "$IMAGEM" --set-env-vars "${VARS[@]}" -o none
else
  # 1 réplica só: o cache, o limite de tentativas de login e a trava do treino ficam na memória
  az containerapp create -n "$API" -g "$RG" --environment "$AMBIENTE" --image "$IMAGEM" \
    --registry-server "$ACR.azurecr.io" --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
    --ingress external --target-port 8000 --min-replicas 1 --max-replicas 1 --cpu 0.5 --memory 1Gi \
    --system-assigned --secrets "${SEGREDOS[@]}" --env-vars "${VARS[@]}" -o none
fi

# a identidade da API pode iniciar o job (e só ele)
PRINCIPAL="$(az containerapp show -n "$API" -g "$RG" --query identity.principalId -o tsv)"
if [ -z "$(az role assignment list --assignee "$PRINCIPAL" --scope "$JOB_ID" --role Contributor --query '[0].id' -o tsv)" ]; then
  for tentativa in 1 2 3 4 5 6; do  # a identidade recém-criada leva um tempo para aparecer
    az role assignment create --assignee-object-id "$PRINCIPAL" --assignee-principal-type ServicePrincipal \
      --role Contributor --scope "$JOB_ID" -o none && break
    [ "$tentativa" = 6 ] && exit 1; echo "   aguardando a identidade da API..."; sleep 20
  done
fi

URL="https://$(az containerapp show -n "$API" -g "$RG" --query properties.configuration.ingress.fqdn -o tsv)"
echo
echo ">> pronto: $URL"
echo "   teste:  curl $URL/health"
echo "   Vercel: VITE_API_URL=$URL (Settings → Environment Variables) e Redeploy"
