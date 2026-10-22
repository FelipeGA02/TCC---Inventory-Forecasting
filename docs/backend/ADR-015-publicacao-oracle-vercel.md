# ADR-015: Publicação — API na Oracle Cloud Always Free (São Paulo), front na Vercel

**Status**: Aceito  
**Data**: 2026-10-22  
**Autores**: Daniel Nunes da Silva, Felipe Gurgel Araújo

---

## Contexto

O sistema precisa ficar acessível para a loja e para a banca sem custo. A API tem três
exigências que eliminam a maioria das hospedagens gratuitas:

- **Ficar perto do banco.** O Neon está em São Paulo (ADR-014) e cada tela faz várias
  consultas. Com o banco em Ohio e a API no Brasil, cada consulta atravessava o continente
  e as telas ficavam lentas.
- **Ficar ligada.** O agendador (ADR-006) roda dentro da API: o treino é disparado
  10 minutos depois de uma planilha com venda nova e, como rede de segurança, toda
  segunda às 02:00. Uma hospedagem que desliga a API sem acesso perde esses gatilhos ou
  mata um treino no meio.
- **Memória e CPU para o treino.** O treino (2 lojas, 26 rodadas de validação, um SARIMAX
  por produto regular) leva cerca de 40 min com 8 processos.

## Decisão

- **API**: máquina virtual **Oracle Cloud Always Free** (Ampere A1, ARM, até 4 OCPUs e
  24 GB) na região **Brazil East (São Paulo)**, com Docker Compose: a API (imagem de
  `ia-predictor/Dockerfile`) atrás do **Caddy**, que cuida do HTTPS (Let's Encrypt) num
  endereço gratuito do DuckDNS. Arquivos em `deploy/`.
- **Front**: **Vercel** (plano gratuito), build do Vite a partir de `app-react/`, com
  `VITE_API_URL` apontando para a API.

## Alternativas avaliadas (out/2026)

| Opção | Por que não |
| --- | --- |
| Render (grátis) | 512 MB e 0,1 CPU, desliga após 15 min sem acesso, sem região na América do Sul: o treino teria de sair da API e o Neon voltar para os EUA |
| Google Cloud Run | desliga sem acesso e corta a CPU fora das requisições (o treino teria de virar um Job separado); cota gratuita em São Paulo não confirmada |
| Hugging Face Spaces | a documentação atual exige plano pago para Space com Docker |
| Koyeb | plano gratuito de servidor deixou de existir em 2026 |
| Fly.io | sem plano gratuito para contas novas (seria a escolha paga: tem região São Paulo) |
| Computador próprio + Cloudflare Tunnel | depende de um computador ligado o tempo todo |

## Consequências

- Custo zero, e a arquitetura fica como foi feita: agendador e treino dentro da API.
- A máquina é nossa para administrar (atualização com `deploy/atualizar.sh`). O
  cadastro na Oracle pede cartão (sem cobrança dentro do Always Free), e às vezes a região
  fica sem capacidade para criar a máquina A1.
- A Oracle pode recuperar máquinas Always Free ociosas. Converter a conta para "Pay As You
  Go" evita isso e continua sem cobrança enquanto o uso ficar dentro do Always Free.
- A imagem é ARM: todas as dependências de `requirements.txt` têm wheel `aarch64` para
  Python 3.14 (conferido em 2026-10-22).
