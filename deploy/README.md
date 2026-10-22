# Publicação: API no Google Cloud Run, front na Vercel

A decisão e as alternativas estão no [ADR-015](../docs/backend/ADR-015-publicacao-cloud-run-vercel.md).

```
navegador ──► Vercel (front estático, grátis)
         └──► Cloud Run "api" (São Paulo) ──► Neon (São Paulo)
                  │ upload com venda nova / botão "Atualizar os modelos"
                  ▼
              Cloud Run Job "treino" (4 CPUs, 8 GB, só enquanto treina) ◄── Cloud Scheduler (seg 02:00)
```

| Arquivo | Para quê |
| --- | --- |
| `../ia-predictor/Dockerfile` | imagem única da API e do Job de treino |
| `../ia-predictor/.gcloudignore` | o que não sobe para o build |
| `configurar.sh` | preparação do projeto, feita **uma vez** |
| `publicar.sh` | build e publicação da API e do Job (a cada atualização) |
| `env.cloudrun.example.yaml` | modelo do `deploy/env.cloudrun.yaml`, que tem as senhas e **nunca vai para o git** |
| `limpeza-imagens.json` | guarda só as 2 últimas imagens, para caber na cota grátis |
| `../app-react/vercel.json` | rotas do React na Vercel |

## Como fica sem custo

Tudo o que o sistema usa cabe na cota grátis mensal do Google Cloud
(<https://cloud.google.com/run/pricing>, conferido em out/2026):

| Recurso | Cota grátis por mês | Uso esperado |
| --- | --- | --- |
| Cloud Run, API | 180 mil vCPU-s, 360 mil GiB-s, 2 milhões de requisições | só conta enquanto responde: `min-instances=0`, CPU só durante a requisição, no máximo 1 instância |
| Cloud Run Jobs, treino | 240 mil vCPU-s, 450 mil GiB-s | um treino de ~1 h com 4 CPUs e 8 GB gasta perto de 15 mil vCPU-s e 30 mil GiB-s: cabem vários por mês |
| Artifact Registry, imagens | 0,5 GB | 1 a 2 imagens (a política apaga as antigas) |
| Cloud Build | 2.500 min de build | ~5 min por publicação |
| Cloud Scheduler | 3 agendamentos | 1 (treino de segunda) |

São Paulo é região "Tier 2". A cota é aplicada como desconto no preço do Tier 1, então lá
ela rende um pouco menos, mas ainda sobra muito para o nosso uso.

**O único custo possível:** a saída de dados para a internet só tem cota grátis dentro da
América do Norte (1 GB/mês). As respostas para quem usa o sistema no Brasil são cobradas
desde o primeiro byte. Com a compressão (gzip) já ligada na API, uma sessão normal
transfere poucos MB, então a conta esperada fica entre zero e alguns centavos de dólar por
mês. O orçamento com alerta (passo 1) avisa se algo sair do esperado.

---

## 0. Antes de começar

- Conta Google e um cartão. O Google pede o cartão para ativar o faturamento, mesmo dentro
  da cota grátis. Conta nova ganha US$ 300 de teste por 90 dias. Ao fim do teste, é preciso
  **ativar a conta paga** no console (não acontece sozinho); a cota grátis continua valendo.
- Google Cloud CLI no Windows (PowerShell):

  ```powershell
  winget install Google.CloudSDK
  ```

  Feche e abra o terminal. Os comandos abaixo rodam no **Git Bash**, na raiz do repositório.

## 1. Projeto, faturamento e alerta de gasto

1. Em <https://console.cloud.google.com>, crie um projeto (ex.: `verde-perto`) e anote o
   **ID do projeto** (aparece embaixo do nome, ex.: `verde-perto-123456`).
2. *Faturamento*: vincule o projeto à conta de faturamento.
3. *Faturamento → Orçamentos e alertas → Criar orçamento*: valor de **R$ 5**, alertas em
   50%, 90% e 100%, enviados por e-mail. O alerta só avisa, não bloqueia; se ele chegar,
   veja em *Faturamento → Relatórios* o que gastou.

## 2. Preparar o projeto (uma vez)

```bash
gcloud auth login
PROJETO=verde-perto-123456 deploy/configurar.sh
```

O script liga as APIs (Cloud Run, Artifact Registry, Cloud Build, Cloud Scheduler), cria o
repositório de imagens com a limpeza automática e agenda o treino de segunda às 02:00.

## 3. Variáveis da API

```bash
cp deploy/env.cloudrun.example.yaml deploy/env.cloudrun.yaml
```

Preencha `deploy/env.cloudrun.yaml` com os mesmos valores do `ia-predictor/.env`
(`DATABASE_URL`, `JWT_SECRET_KEY`, senhas). `CORS_ORIGINS` fica `'[]'` por enquanto.

## 4. Publicar a API e o Job de treino

```bash
PROJETO=verde-perto-123456 deploy/publicar.sh
```

Leva uns 5 a 10 minutos: build da imagem, Job `treino` e serviço `api`. No fim, o script
mostra o endereço da API (`https://api-xxxxx.southamerica-east1.run.app`). Para testar:

```bash
curl https://api-xxxxx.southamerica-east1.run.app/health
```

A API desliga quando ninguém usa. O primeiro acesso depois de um tempo parado leva alguns
segundos a mais, enquanto ela sobe.

## 5. Publicar o front na Vercel

1. Em <https://vercel.com>: *Add New → Project* e importe o repositório do GitHub.
2. **Root Directory**: `app-react`. O resto (Vite, `npm run build`, `dist`) é detectado
   sozinho.
3. *Environment Variables*: `VITE_API_URL` = o endereço da API do passo 4.
4. *Deploy*, e anote o endereço do front (ex.: `https://verde-perto.vercel.app`).
5. Libere esse endereço na API: em `deploy/env.cloudrun.yaml`, coloque
   `CORS_ORIGINS: '["https://verde-perto.vercel.app"]'` e rode o `publicar.sh` de novo.

## 6. Primeiro treino pelo backend

A previsão que está no banco foi importada do treino offline. Para gerar a primeira pelo
Job:

1. Abra `https://<endereço da API>/docs`, clique em *Authorize* e entre com o e-mail e a
   senha da gestora (admin).
2. Em `POST /api/v1/models/retrain`, use *Try it out → Execute*.
3. Acompanhe em *Cloud Run → Jobs → treino → Execuções → Logs*. Quando terminar, a tela
   de previsão mostra a previsão nova.

Daí em diante, o treino roda sozinho: 10 minutos depois de uma planilha com venda nova e
toda segunda às 02:00 (pulado se não houver venda nova).

## 7. Atualizar depois de um merge na `main`

- **Front**: a Vercel publica sozinha a cada push na `main` e cria uma prévia de cada PR.
- **API e Job**: `PROJETO=... deploy/publicar.sh` a partir da `main` atualizada.

## Problemas comuns

| Sintoma | O que ver |
| --- | --- |
| `publicar.sh` falha no build com erro de permissão | *IAM*: a conta `<número>-compute@developer.gserviceaccount.com` precisa do papel *Editor* (projetos pessoais já vêm assim) |
| Front abre, mas o login dá erro de rede | `CORS_ORIGINS` sem o endereço exato da Vercel (com `https://`, sem `/` no fim) e o `publicar.sh` não foi rodado de novo |
| Upload funciona, mas a previsão não muda | *Cloud Run → Jobs → treino → Execuções*: a execução falhou ou foi pulada; os logs explicam |
| Treino morre por memória (logs com `OOM` ou `Memory limit`) | suba `--memory` do Job no `publicar.sh` (até 32Gi) ou baixe `TRAINING_WORKERS` |
| API não sobe (logs com erro de validação) | valor em formato errado no `env.cloudrun.yaml`, ex.: `CORS_ORIGINS` precisa ser uma lista JSON entre aspas simples |
