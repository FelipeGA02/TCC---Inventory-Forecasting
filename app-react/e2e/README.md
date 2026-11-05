# Testes de ponta a ponta (Playwright)

Testam o sistema como a loja usa: o navegador abre o front (React) e o front conversa com a
API de verdade (FastAPI). Cada fluxo tira fotos das telas em `e2e/fotos/`.

## Como rodar

Uma vez na máquina:

```bash
# API: ambiente virtual com as dependências (em ia-predictor/)
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # Linux/macOS: .venv/bin/python

# Front (em app-react/)
npm ci
npm run e2e:instalar        # baixa o Chromium do Playwright
```

Depois, em `app-react/`:

```bash
npm run e2e                 # roda todos os testes e tira as fotos
npm run e2e -- 04-previsao  # só um arquivo
npm run e2e:ui              # modo interativo (ver cada passo, repetir um teste)
npm run e2e:relatorio       # relatório HTML da última execução (com trace dos que falharam)
```

O Playwright sobe sozinho a API na porta **8100** e o front na **5174**, sem conflito com o
`npm run dev` (5173) e a API de desenvolvimento (8000). Não precisa de `.env`.

A **primeira execução demora alguns minutos**: monta a base sintética e treina a previsão
(o mesmo treino do botão "Treinar previsões", com 14 origens no walk-forward em vez de 56).
A base fica em cache em `ia-predictor/tests/e2e/.cache/`; as execuções seguintes começam em
segundos.

Se o Python não estiver em `ia-predictor/.venv`, aponte com `E2E_PYTHON=/caminho/python`.

## Banco dos testes: nunca o Neon

A API dos testes (`ia-predictor/tests/e2e/servidor.py`) usa um **SQLite próprio** com uma
base sintética: 2 lojas, 4 categorias, 3 produtos de grama, de 02/01/2025 a 28/02/2026, com
feriados, ciclo semanal e algumas encomendas grandes. As variáveis de ambiente dela têm
prioridade sobre o `.env`, então os testes nunca tocam o banco compartilhado, mesmo com o
`.env` apontando para o Neon. Cada execução começa de uma cópia limpa do cache: o que os
testes gravam (planilha enviada, treino disparado) some na próxima.

Usuários dos testes (só existem nesse banco): `gestora@floricultura.com` / `senha-admin-e2e`
e `gerente@floricultura.com` / `senha-viewer-e2e`.

Mudou a base sintética, o calendário ou a configuração do treino? Suba `VERSAO_BASE` em
`servidor.py` para refazer o cache.

## Fluxos cobertos

Os arquivos rodam em ordem, um de cada vez (compartilham o banco da execução):

| Arquivo | Fluxo | Perfil |
| --- | --- | --- |
| `01-login` | login, senha errada, volta à página pedida, sessão após recarregar, sair | os dois |
| `02-inicio` | indicadores, gráficos, filtro de loja, faturamento × quantidade, Atualizar | gestora |
| `03-conferir-dados` | abas, busca, filtros, nota, colunas, exportar Excel/CSV | gerente |
| `04-previsao` | 14 dias por categoria e por produto de grama, dia a dia, histórico | gerente |
| `05-relatorios` | gerencial, prévia de cada relatório, download Excel/CSV | gerente |
| `06-importar-planilha` | arquivo inválido, conferência, gravação, planilha repetida, dias faltando | gestora |
| `07-treinar-previsoes` | sino, confirmação, disparo do treino, andamento | gestora |
| `08-perfil-consulta` | sem botão de treino, importação bloqueada | gerente |

`06` grava vendas novas (02 a 07/03/2026) e `07` treina com elas: por isso rodam depois das
telas de consulta. As planilhas são geradas por `preparar.ts` em `e2e/.saida/` (fora do git),
no layout do relatório "Contas a Receber".

## Fotos

`e2e/fotos/<fluxo>-<passo>.png` são recriadas a cada execução, com a página inteira (não só
a parte visível) e sem animações. Podem ir para o git e para o artigo como documentação das
telas. Os dados são sintéticos, então nenhuma venda real aparece.
