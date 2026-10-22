# ADR-015: Publicação: API e treino no Google Cloud Run, front na Vercel

**Status**: Aceito  
**Data**: 2026-10-22  
**Autores**: Daniel Nunes da Silva, Felipe Gurgel Araújo

---

## Contexto

O sistema precisa ficar acessível para a loja e para a banca, sem custo. Três exigências
da API eliminam a maioria das hospedagens gratuitas:

- **Ficar perto do banco.** O Neon está em São Paulo (ADR-014), e cada tela faz várias
  consultas. Com o banco em Ohio e a API no Brasil, cada consulta atravessava o continente e
  as telas ficavam lentas.
- **Memória.** A API usa ~300 MB, com pico de ~420 MB ao subir (medido em 2026-10-22). A
  exportação da base inteira chegava a ~830 MB.
- **Treino.** O treino (2 lojas, 26 rodadas de validação, um SARIMAX por produto regular)
  leva ~40 min com 8 processos e precisa de vários GB. Ele é disparado depois de uma
  planilha com venda nova e toda segunda às 02:00, e é pulado quando não há venda nova.

## Decisão

- **API**: serviço do **Cloud Run** em `southamerica-east1` (São Paulo), com 1 vCPU e
  1 GiB. Cobrança por requisição (a CPU só existe durante a requisição), 0 instâncias sem
  uso e no máximo 1.
- **Treino**: **Job do Cloud Run** na mesma região, com 4 vCPUs e 8 GiB, que só existe
  enquanto treina. Usa a mesma imagem, com o comando `python -m backend.scripts.treinar_job`.
  A API não pode treinar nem esperar em segundo plano (fora da requisição não tem CPU), então
  só registra o pedido (`retrain_history.status = pending`) e inicia o Job pela Cloud Run
  Admin API (`TRAINING_RUNNER=cloud_run_job`). Quem faz a espera de 10 minutos após o upload
  é o Job. O **Cloud Scheduler** inicia o Job toda segunda às 02:00.
- **Exportação** em pedaços (*streaming*): o Cloud Run não aceita resposta única acima de
  32 MB, e a base inteira passa de 40 MB.
- **Front**: **Vercel** (plano gratuito), com o build do Vite em `app-react/`.
- O modo `local` (treino em thread e APScheduler dentro da API) continua sendo o padrão
  para desenvolvimento e para um servidor sempre ligado.

## Alternativas avaliadas (out/2026)

| Opção | Por que não |
| --- | --- |
| Oracle Cloud Always Free (VM em São Paulo) | atende tudo, mas a máquina fica sob nossa administração (sistema, Docker, HTTPS) e a região às vezes fica sem capacidade |
| Render (grátis) | 512 MB e 0,1 CPU; desliga após 15 min e demora ~1 min para voltar; sem região na América do Sul; o treino teria de ir para fora (GitHub Actions) |
| Hugging Face Spaces | a documentação atual exige plano pago para Space com Docker |
| Koyeb | o plano gratuito de servidor deixou de existir em 2026 |
| Fly.io | sem plano gratuito para contas novas |

## Consequências

- A cota grátis mensal do Cloud Run (serviço e Jobs), do Artifact Registry (0,5 GB, com a
  política que guarda só 2 imagens), do Cloud Build e do Cloud Scheduler cobre o uso
  esperado. A conta depende de um cartão e de um orçamento com alerta.
- A saída de dados para a internet só tem cota grátis na América do Norte. As respostas
  para o Brasil podem custar centavos por mês, e a compressão gzip da API reduz isso.
- O primeiro acesso depois de um tempo sem uso leva alguns segundos, enquanto a API sobe.
- As senhas vão como variáveis de ambiente do serviço (`deploy/env.cloudrun.yaml`, fora do
  git), visíveis só para quem administra o projeto. O Secret Manager seria o passo seguinte.
- A imagem é a mesma para a API e o Job. Atualizar é rodar `deploy/publicar.sh`.
