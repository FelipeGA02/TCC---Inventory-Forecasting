#!/usr/bin/env bash
# Build da imagem dentro do Azure, sem Docker local e sem ACR Tasks (bloqueado no Azure for
# Students): o código de ia-predictor/ vai num .tar.gz para um compartilhamento do Azure Files,
# montado num Container Apps Job com o kaniko, que monta a imagem e a envia ao registro (o
# contexto direto do Blob Storage tem um bug no kaniko 1.23: duplica o caminho do blob).
# Chamado por publicar.sh, com as variáveis RAIZ, RG, LOC, ACR, ACR_USER, ACR_PASS,
# AMBIENTE_ID, COMMIT e IMAGEM.
set -euo pipefail

CONTA="${ACR:0:24}"                     # conta de armazenamento: mesmo nome do registro
COMPARTILHAMENTO=build
BUILDER=verde-perto-build
# imagem -debug: tem shell, para gravar a credencial do registro antes do build
KANIKO=gcr.io/kaniko-project/executor:v1.23.2-debug

az storage account show -n "$CONTA" -g "$RG" -o none 2>/dev/null \
  || az storage account create -n "$CONTA" -g "$RG" -l "$LOC" --sku Standard_LRS --min-tls-version TLS1_2 \
       --allow-blob-public-access false -o none
CHAVE="$(az storage account keys list -n "$CONTA" -g "$RG" --query '[0].value' -o tsv)"
az storage share create -n "$COMPARTILHAMENTO" --account-name "$CONTA" --account-key "$CHAVE" --quota 1 -o none
az containerapp env storage set -n "${AMBIENTE_ID##*/}" -g "$RG" --storage-name build \
  --azure-file-account-name "$CONTA" --azure-file-account-key "$CHAVE" \
  --azure-file-share-name "$COMPARTILHAMENTO" --access-mode ReadOnly -o none

# contexto: arquivos versionados e novos (não ignorados) de ia-predictor/, como estão no disco;
# o kaniko ainda aplica o .dockerignore
TMP="$(mktemp -d)"; TMP="$(cygpath -m "$TMP" 2>/dev/null || echo "$TMP")"; trap 'rm -rf "$TMP"' EXIT
( cd "$RAIZ/ia-predictor" && git ls-files -co --exclude-standard -z \
    | xargs -0 -I{} sh -c 'test -e "{}" && printf "%s\n" "{}"' > "$TMP/lista" \
    && tar --force-local -czf "$TMP/contexto.tar.gz" -T "$TMP/lista" )
ARQUIVO="contexto-$COMMIT-$(date +%s).tar.gz"
az storage file upload --account-name "$CONTA" --account-key "$CHAVE" -s "$COMPARTILHAMENTO" \
  --path "$ARQUIVO" --source "$TMP/contexto.tar.gz" -o none --only-show-errors
echo "   contexto enviado ($(du -h "$TMP/contexto.tar.gz" | cut -f1))"

AUTH="$(printf '%s:%s' "$ACR_USER" "$ACR_PASS" | base64 | tr -d '\n')"
DOCKER_CONFIG_JSON="{\"auths\":{\"$ACR.azurecr.io\":{\"auth\":\"$AUTH\"}}}"

cat > "$TMP/job.yaml" <<EOF
location: $LOC
properties:
  environmentId: $AMBIENTE_ID
  configuration:
    triggerType: Manual
    replicaTimeout: 3600
    replicaRetryLimit: 0
    manualTriggerConfig: {parallelism: 1, replicaCompletionCount: 1}
    secrets:
      - {name: docker-config, value: '$DOCKER_CONFIG_JSON'}
  template:
    containers:
      - name: kaniko
        image: $KANIKO
        command: [/busybox/sh, -c]
        args:
          - >-
            printf '%s' "\$DOCKER_CONFIG_JSON" > /kaniko/.docker/config.json &&
            exec /kaniko/executor --context=tar:///contexto/$ARQUIVO
            --destination=$IMAGEM --build-arg=GIT_COMMIT=$COMMIT --snapshot-mode=redo --use-new-run
        resources: {cpu: 2, memory: 4Gi}
        env:
          - {name: DOCKER_CONFIG_JSON, secretRef: docker-config}
        volumeMounts:
          - {volumeName: contexto, mountPath: /contexto}
    volumes:
      - {name: contexto, storageType: AzureFile, storageName: build}
EOF
# o job é recriado a cada build (o contexto muda de nome)
az containerapp job delete -n "$BUILDER" -g "$RG" --yes -o none 2>/dev/null || true
az containerapp job create -n "$BUILDER" -g "$RG" --yaml "$TMP/job.yaml" -o none
EXEC="$(az containerapp job start -n "$BUILDER" -g "$RG" --query name -o tsv)"
echo "   build em andamento (execução $EXEC)..."
while :; do
  sleep 20
  ESTADO="$(az containerapp job execution show -n "$BUILDER" -g "$RG" --job-execution-name "$EXEC" \
            --query properties.status -o tsv 2>/dev/null || echo Desconhecido)"
  case "$ESTADO" in
    Succeeded) echo "   imagem pronta: $IMAGEM"; break ;;
    Failed|Stopped|Degraded)
      echo "!! build falhou ($ESTADO). Log: az containerapp job logs show -n $BUILDER -g $RG --execution $EXEC --container kaniko"
      exit 1 ;;
  esac
done
az storage file delete --account-name "$CONTA" --account-key "$CHAVE" -s "$COMPARTILHAMENTO" -p "$ARQUIVO" \
  -o none --only-show-errors || true
