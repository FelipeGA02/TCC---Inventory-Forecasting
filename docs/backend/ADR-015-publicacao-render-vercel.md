# ADR-015: Publicação: API no Render, front na Vercel, treino fora da API

**Status**: Aceito (o treino mudou com o [ADR-017](../prediction/ADR-017-previsao-por-categoria-e-grama.md), ver o fim)  
**Data**: 2026-10-22  
**Autores**: Daniel Nunes da Silva, Felipe Gurgel Araújo

---

## Contexto

O sistema precisa ficar acessível para a loja e para a banca **sem custo e sem
pagamento antecipado**. Medições da API (2026-10-22):

- **Memória:** ~300 MB de uso, com pico de ~420 MB ao subir. A exportação da base inteira
  chegava a ~830 MB; passou a ser enviada em pedaços e não sobe mais o pico.
- **CPU:** carregar o código consome ~10 s de CPU; metade disso era o `statsmodels`, que a
  API só usa para treinar. Ele passou a ser carregado só no treino.
- **Treino:** 2 lojas, 26 rodadas de validação, um SARIMAX por produto regular. Leva ~40 min
  com 8 processos e vários GB.

## Decisão

- **API**: plano grátis do **Render** (512 MB, 0,1 CPU, sem cartão), na região Virgínia,
  com a imagem de `ia-predictor/Dockerfile` e a configuração no `render.yaml` (*Blueprint*).
  Publica sozinha a cada push na `main`.
- **Treino fora da API** (`TRAINING_RUNNER=externo`): a API não treina nem agenda treino.
  A previsão é atualizada quando a equipe roda `python -m backend.scripts.gravar_previsao`
  de uma máquina sua, sobre o mesmo banco. O treino semanal e o treino após o upload
  continuam no modo `local`, para desenvolvimento ou para um servidor com memória sobrando.
- **Front**: **Vercel** (plano grátis), com o build do Vite em `app-react/`.

## Alternativas avaliadas (out/2026)

| Opção | Por que não |
| --- | --- |
| Google Cloud Run (API + Job de treino, cota grátis) | ativar o faturamento pediu um pré-pagamento de R$ 150 (reembolsável), que a equipe não quis fazer |
| Oracle Cloud Always Free (VM em São Paulo) | pede cartão; a máquina fica sob nossa administração; a região às vezes fica sem capacidade |
| Koyeb | o plano grátis passou a exigir cartão com bloqueio de US$ 29 |
| Hugging Face Spaces | a documentação atual exige plano pago para Space com Docker |
| Fly.io, Railway, Heroku | sem plano grátis permanente para contas novas |

## Consequências

- Custo zero, sem cartão.
- A API dorme após 15 minutos sem acesso. O primeiro acesso depois disso leva de 1 a
  3 minutos, e com CPU de 0,1 cada tela é mais lenta que no desenvolvimento.
- O Render não tem região na América do Sul: cada consulta ao Neon (São Paulo) atravessa
  o continente. Se ficar lento demais, dá para criar um projeto do Neon na Virgínia e
  recarregar o banco com os scripts de carga.
- O upload de planilha grava as vendas, mas a previsão só muda depois do treino rodado
  pela equipe. O front esconde o botão "Atualizar os modelos" (`treino_na_api` falso em
  `/contexto`).
- Render e Vercel precisam de acesso ao repositório privado pela conta dona dele no GitHub.

## Revisão (2026-10-26, ADR-017)

O treino da previsão passou a ser o das 4 categorias e dos produtos de grama, por loja, e
não roda mais sozinho: não há treino semanal nem após o upload em nenhum modo. No Render
(`TRAINING_RUNNER=externo`) a equipe roda `python -m backend.scripts.treinar_previsoes`
(no lugar de `gravar_previsao`) de uma máquina sua, sobre o mesmo banco, e o front esconde o
botão "Treinar previsões". No modo `local` o botão treina numa thread da API.
