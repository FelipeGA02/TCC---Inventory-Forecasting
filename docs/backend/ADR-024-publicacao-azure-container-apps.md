# ADR-024 — API no Azure Container Apps, com o treino num job

**Status:** Aceito · **Data:** 2026-11-16 · **Revisa:** [ADR-015](ADR-015-publicacao-render-vercel.md) (só a API; front na Vercel e banco no Neon continuam)

## Contexto

No Render grátis (ADR-015) a API tem 512 MB e 0,1 CPU, dorme depois de 15 minutos e não
treina (`TRAINING_RUNNER=externo`): a previsão só mudava quando alguém da equipe rodava
`treinar_previsoes` de outra máquina. A equipe tem US$ 200 de crédito do Azure for Students.

O treino (ADR-017, d escolhido série a série pelo ADR-020) precisa de vários processos por
algumas dezenas de minutos, uma vez por semana. Manter uma máquina desse tamanho ligada o mês
inteiro gastaria o crédito em poucos meses.

## Decisão

- **API**: Azure Container App em Brazil South (mesma região do Neon), 0,5 vCPU e 1 GiB, uma
  réplica sempre ligada (o cache, o limite de tentativas de login e a trava do treino ficam na
  memória do processo).
- **Treino**: Container Apps Job manual, 4 vCPU e 8 GiB, com a mesma imagem e o comando
  `python -m backend.scripts.treinar_previsoes --pendente`. Ele só liga quando a gestora clica
  em "Treinar previsões" e só é cobrado enquanto roda.
- **Novo `TRAINING_RUNNER=azure_job`**: o botão registra o disparo como `pending` em
  `forecast_jobs` (ou `skipped`, sem dados novos) e inicia o job pela API de gerenciamento do
  Azure, com a identidade gerenciada do Container App (papel *Contributor* só no job, sem
  segredo guardado). O job pega o disparo pendente (`servico_previsao.executar_pendente`) e
  grava o andamento no Neon; a tela acompanha como no treino local. Disparo pendente que o job
  não pega em 15 minutos vira `error`; se o Azure recusar o pedido, o disparo vira `error` na
  hora e a API responde 503 com mensagem em PT-BR.
- **Build da imagem no próprio Azure, com o kaniko** num job temporário: o Azure for Students
  bloqueia o ACR Tasks e a máquina da equipe não tem Docker. Detalhes e os outros limites
  encontrados em [`deploy/azure/README.md`](../../deploy/azure/README.md).
- O script `deploy/azure/publicar.sh` cria tudo na primeira vez e publica a imagem nova nas
  seguintes. O commit vai na imagem (`GIT_COMMIT`) e fica gravado em cada treino.

## Alternativas

| Opção | Por que não |
| --- | --- |
| Treino numa thread da API (`local`) num App Service B2/B3 | 2–4 vCPU ligados o mês todo: US$ 26–75/mês, o crédito acaba em 3–7 meses |
| App Service B1 sem treino (`externo`) | mais barato, mas o botão continua sem funcionar |
| Treino automático depois de cada planilha | a loja envia mais de uma planilha por semana; o treino ficaria rodando de novo a cada envio. O botão continua sendo o disparo, como no ADR-017 |
| Build com GitHub Actions | exige segredos no repositório, que pertence a outro integrante |

## Consequências

- O botão "Treinar previsões" volta a aparecer na instalação publicada (`treino_na_api`
  verdadeiro para `local` e `azure_job`).
- Custo estimado: ~US$ 15–25/mês (API, registro, logs) mais ~US$ 0,50 por hora de treino.
- O treino começa 1 a 3 minutos depois do clique (o contêiner sobe).
- `render.yaml` e o modo `externo` continuam no código: o Render pode voltar se o crédito acabar.
