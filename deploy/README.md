# Publicação: API no Render, front na Vercel (planos grátis, sem cartão)

A decisão e as alternativas estão no [ADR-015](../docs/backend/ADR-015-publicacao-render-vercel.md).

```
navegador ──► Vercel (front estático)
         └──► Render "verde-perto-api" (Virgínia, EUA) ──► Neon (São Paulo)

treino (fora da API): python -m backend.scripts.treinar_previsoes, numa máquina da equipe ──► Neon
```

| Arquivo | Para quê |
| --- | --- |
| `../render.yaml` | configuração do serviço no Render (*Blueprint*) |
| `../ia-predictor/Dockerfile` | imagem da API |
| `../app-react/vercel.json` | rotas do React na Vercel |

## O que o plano grátis do Render dá (e não dá)

- 512 MB de memória e 0,1 CPU. A API usa ~300 MB, com pico de ~420 MB (medido).
- **Dorme depois de 15 minutos sem acesso.** O primeiro acesso depois disso leva de 1 a
  3 minutos (o Render acorda o serviço e a API sobe com CPU baixa). Com a API acordada,
  as telas respondem em segundos.
- 750 horas por mês: dá para um serviço o mês inteiro.
- **A API não treina** (`TRAINING_RUNNER=externo`): não há memória nem CPU para isso. O
  upload de planilha funciona e grava as vendas, mas a previsão só muda quando a equipe
  roda o treino (passo 6). O botão "Treinar previsões" não aparece nessa instalação.

## 1. Acesso ao repositório

O repositório é privado e pertence a `FelipeGA02`. Render e Vercel leem o código por um
app do GitHub instalado **na conta dona do repositório**. Então o Felipe faz o login com o
GitHub dele no Render e na Vercel, ou instala os apps dando acesso a este repositório.

## 2. Criar a API no Render

1. Em <https://render.com>, entre com o GitHub (não pede cartão).
2. *New → Blueprint* e escolha o repositório `TCC---Inventory-Forecasting`. O Render lê o
   `render.yaml` da `main`.
3. Preencha as variáveis pedidas com os mesmos valores do `ia-predictor/.env`:
   `DATABASE_URL`, `JWT_SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `VIEWER_EMAIL`,
   `VIEWER_PASSWORD`. Em `CORS_ORIGINS`, coloque `[]` por enquanto.
4. *Apply*. O primeiro build leva uns 10 minutos. No fim, o serviço mostra o endereço
   (`https://verde-perto-api.onrender.com`). Para testar:

   ```bash
   curl https://verde-perto-api.onrender.com/health
   ```

## 3. Publicar o front na Vercel

1. Em <https://vercel.com>: *Add New → Project* e importe o repositório.
2. **Root Directory**: `app-react`. O resto (Vite, `npm run build`, `dist`) é detectado
   sozinho.
3. *Environment Variables*: `VITE_API_URL` = o endereço da API do passo 2.
4. *Deploy*, e anote o endereço do front (ex.: `https://verde-perto.vercel.app`).

## 4. Liberar o front na API

No Render: serviço → *Environment* → `CORS_ORIGINS` = `["https://verde-perto.vercel.app"]`
(o endereço exato, com `https://` e sem `/` no fim) → *Save*. O Render publica de novo
sozinho.

## 5. Atualizações

Cada push na `main` publica de novo a API (Render) e o front (Vercel). A Vercel também cria
uma prévia de cada PR.

## 6. Atualizar a previsão (treino)

Quando entrarem planilhas novas, alguém da equipe roda o treino das categorias e dos
produtos de grama (ADR-017) de uma máquina com o `ia-predictor/.env` apontando para o Neon.
Cada série leva uns 4 minutos num processo; `--workers` divide entre processos (no
proot/Termux use 1):

```bash
cd ia-predictor
python -m backend.scripts.treinar_previsoes --workers 8
```

Se os dados não mudaram desde o último treino, o script registra o disparo como `skipped` e
termina. A previsão nova aparece nas telas assim que ele conclui: a API percebe pela tabela
`forecast_jobs` e refaz o cache. O log de cada série fica em `forecast_job_logs`.

## Problemas comuns

| Sintoma | O que ver |
| --- | --- |
| Primeiro acesso demora ou dá erro de rede | a API estava dormindo; espere 1 a 3 minutos e recarregue |
| Front abre, mas o login dá erro de rede (com a API acordada) | `CORS_ORIGINS` sem o endereço exato da Vercel; ou a API fora de `*.onrender.com` — inclua o endereço em `connect-src` no `app-react/vercel.json` |
| Deploy falha no Render com erro de memória | o build ou a subida passou de 512 MB; veja os logs do serviço |
| API não sobe (logs com erro de validação) | valor em formato errado numa variável, ex.: `CORS_ORIGINS` precisa ser uma lista JSON |
| API não sobe (`RuntimeError: Configure no .env ou nas variáveis do servidor`) | `JWT_SECRET_KEY` vazia, com menos de 32 caracteres ou de exemplo, ou `ADMIN_PASSWORD`/`VIEWER_PASSWORD` vazia, com menos de 8 ou de exemplo — a mensagem diz qual |
| Login responde "Muitas tentativas com senha errada" | 5 senhas erradas seguidas para o e-mail (ou 20 de vários lugares) bloqueiam por 15 minutos; reiniciar o serviço também libera |
| Todos precisam entrar de novo logo depois de publicar a versão com logout no servidor | esperado, uma vez só: as sessões abertas antes dela não podem ser encerradas no logout e por isso são recusadas |
