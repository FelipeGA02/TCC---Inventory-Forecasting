# Publicação da API no Azure (Azure for Students)

Front na Vercel e banco no Neon continuam como estão (ver [../README.md](../README.md)); só a
API sai do Render. No Azure o botão **"Treinar previsões"** volta a funcionar: o treino roda
num contêiner separado, maior, que só liga quando a gestora clica.

```
navegador ──► Vercel (front) ──► Container App "verde-perto-api" (Brazil South) ──► Neon (São Paulo)
                                     │ botão "Treinar previsões"
                                     ▼
                               Container Apps Job "verde-perto-treino" (4 vCPU, 8 GiB) ──► Neon
```

| Recurso | Tamanho | Custo aproximado |
| --- | --- | --- |
| `verde-perto-api` (Container App) | 0,5 vCPU, 1 GiB, 1 réplica sempre ligada | ~US$ 10–20/mês (consumo; parte entra na cota grátis mensal) |
| `verde-perto-treino` (Container Apps Job) | 4 vCPU, 8 GiB, só enquanto treina | ~US$ 0,50 por hora de treino |
| `verdeperto…` (Container Registry Basic) | guarda a imagem | ~US$ 5/mês |
| `verdeperto…` (Storage, Azure Files) | código enviado para o build | centavos |
| `verde-perto-build` (Container Apps Job, kaniko) | 2 vCPU, 4 GiB, só durante o build | centavos por build |
| Log Analytics (criado com o ambiente) | logs da API e do treino | poucos centavos com o volume do projeto |

Os valores são estimativas da tabela de preços; confira em *Cost Management* e crie um
alerta de orçamento (passo 5).

## Como o treino funciona aqui (`TRAINING_RUNNER=azure_job`)

1. A gestora envia a planilha e clica em "Treinar previsões".
2. A API registra o disparo como `pending` em `forecast_jobs` (ou `skipped`, sem dados
   novos — aí nada liga) e pede ao Azure para iniciar o job, com a identidade gerenciada dela
   (sem senha guardada; ela só tem permissão sobre o job).
3. O job sobe em 1 a 3 minutos, roda `python -m backend.scripts.treinar_previsoes --pendente`,
   pega o disparo pendente e treina com 4 processos, gravando o andamento no Neon. A tela de
   notificações mostra o progresso como no treino local.
4. No fim o contêiner desliga e para de cobrar.

Se o job não pegar o disparo em 15 minutos, ele vira `error` e o botão volta a funcionar.
O script continua servindo de outra máquina, como antes.

## 1. Conta e Azure CLI

O Azure CLI desta máquina pode estar logado em outra conta (de trabalho). Entre com a conta
do Azure for Students e escolha a assinatura dela:

```bash
az login                      # no navegador, a conta do Azure for Students
az account list -o table      # ache "Azure for Students"
az account set --subscription "Azure for Students"
az account show -o table      # confira antes de seguir
```

A conta da faculdade exige MFA para **criar** recursos (ler funciona sem). Se o script
parar com `AADSTS50076 ... must use multi-factor authentication`, entre de novo pedindo o
MFA, por código (o retorno do navegador para o CLI não funcionou nesta máquina):

```bash
az login --use-device-code --tenant "<id do tenant da faculdade>"   --scope "https://management.core.windows.net//.default"   --claims-challenge "<o valor que o erro mostra>"
az account set --subscription "Azure for Students"
```

## 2. Variáveis

```bash
cp deploy/azure/env.azure.example deploy/azure/.env.azure   # fora do git (.env.*)
```

Preencha com os valores do `ia-predictor/.env` e a `DATABASE_URL` do Neon. Em
`CORS_ORIGINS`, o endereço exato do front na Vercel.

## 3. Publicar

Da raiz do repositório, no Git Bash:

```bash
bash deploy/azure/publicar.sh
```

Na 1ª vez cria o grupo `verde-perto`, o registro, o ambiente, o job e a API (~15 minutos,
quase tudo no build da imagem, que roda no próprio Azure — não precisa de Docker).

### Por que o build é assim (limites do Azure for Students)

- **ACR Tasks (`az acr build`) é bloqueado** na assinatura de estudante
  (`TasksOperationsNotAllowed`). O `build_imagem.sh` faz o build com o
  [kaniko](https://github.com/GoogleContainerTools/kaniko) num Container Apps Job: o código
  de `ia-predictor/` vai num `.tar.gz` para um compartilhamento do Azure Files, montado no
  job, e o kaniko envia a imagem ao registro.
- **O contexto direto do Blob Storage não serve**: o kaniko 1.23 duplica o caminho do blob
  (`BlobNotFound`). Por isso o Azure Files.
- **O ambiente precisa ser `WorkloadProfiles`**: o CLI novo cria ambientes *Express* por
  padrão, e eles não aceitam jobs (`ExpressEnvironmentResourceNotSupported`).
- **Volume de segredo em job deu erro interno** no Azure: a credencial do registro entra por
  variável de ambiente e o shell da imagem `-debug` do kaniko grava o `config.json`.
- **Providers**: a assinatura nova precisa de `Microsoft.App`, `Microsoft.OperationalInsights`,
  `Microsoft.ContainerRegistry` e `Microsoft.Storage` registrados (o script registra). No fim
mostra o endereço, algo como `https://verde-perto-api.<algo>.brazilsouth.azurecontainerapps.io`.

```bash
curl https://verde-perto-api.<algo>.brazilsouth.azurecontainerapps.io/health
```

Se a assinatura de estudante não permitir Brazil South, use outra região em
`AZ_LOCATION` (ex.: `eastus`) no `.env.azure`.

## 4. Apontar o front

1. Vercel → projeto → *Settings → Environment Variables*: `VITE_API_URL` = o endereço do
   passo 3. *Redeploy*.
2. O `app-react/vercel.json` já libera `https://*.azurecontainerapps.io` em `connect-src`
   (vale depois do push na `main`).

## 5. Alerta de orçamento

Portal → *Cost Management → Budgets → Add*: escopo a assinatura, valor mensal (ex.:
US$ 25), alerta por e-mail em 80%.

## Atualizações

Cada mudança de código: commit e `bash deploy/azure/publicar.sh` de novo. O script faz o
build da `HEAD` e troca a imagem da API e do job (o commit fica gravado em cada treino).

## Problemas comuns

| Sintoma | O que ver |
| --- | --- |
| Botão responde "Não foi possível iniciar o treino no servidor" | a identidade da API sem o papel *Contributor* no job (rode o script de novo) ou `AZURE_TRAINING_JOB_ID` errado; log em *verde-perto-api → Log stream* |
| Treino fica "na fila" e vira erro depois de 15 min | o job não subiu: *verde-perto-treino → Execution history* mostra a execução e o log |
| API não sobe | *verde-perto-api → Log stream*; a mensagem diz qual variável falta |
| Login com erro de rede no front | `CORS_ORIGINS` sem o endereço exato da Vercel, ou `VITE_API_URL` sem redeploy |
| Treinar à mão, sem o botão | portal: *verde-perto-treino → Run now* (sem disparo pendente, treina como o script; `skipped` sem dados novos) |
