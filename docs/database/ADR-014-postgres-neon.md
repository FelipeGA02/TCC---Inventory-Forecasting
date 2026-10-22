# ADR-014: Postgres gerenciado no Neon

**Status**: Aceito — revisa o [ADR-005](ADR-005-sqlite-vs-postgresql.md)  
**Data**: 2026-10-19  
**Autores**: Daniel Nunes da Silva, Felipe Gurgel Araújo

---

## Contexto

O ADR-005 escolheu SQLite porque o sistema rodaria num servidor local da loja, sem
administração. Duas coisas mudaram:

- A planilha não é mais guardada (`docs/database/modelo_dados.drawio`): o banco passa a ser
  a única cópia da base de vendas, então precisa de backup e de acesso fora de uma máquina só.
- A equipe (dois autores, orientador e loja) precisa ver os mesmos dados sem copiar o
  arquivo `floricultura.db` de um lado para o outro.

## Decisão

**Postgres no Neon** (serverless, plano gratuito) para o banco compartilhado, via
SQLAlchemy 2.0 e o driver `psycopg` 3. O SQLite continua sendo o padrão de
`DATABASE_URL` para desenvolvimento e testes locais: o ORM não usa nada específico de
nenhum dos dois.

## Justificativa

- **Sem servidor para administrar**, como o SQLite: o Neon cuida de backup, versão e
  disponibilidade, e suspende o servidor quando ninguém usa.
- **Backup e histórico**: o Neon guarda o histórico de alterações (restauração a um ponto
  no tempo) e cria *branches* do banco, úteis para testar uma recarga sem mexer nos dados
  oficiais.
- **Escritas concorrentes**: carga de planilha, treino e leitura do painel ao mesmo tempo,
  sem a trava de arquivo do SQLite.
- **Cabe no plano gratuito**: a base inteira (351 mil vendas, 5,2 mil produtos, calendário)
  ocupa ~65 MB no SQLite e algo perto de 100 MB no Postgres, com índices; o limite do
  plano é 0,5 GB.

## Consequências

- `DATABASE_URL` no `ia-predictor/.env` recebe a URL do console do Neon
  (`postgresql://...neon.tech/neondb?sslmode=require`); `database_url()` em
  `backend/infrastructure/database.py` troca o prefixo pelo do psycopg.
- O engine usa `pool_pre_ping` e `pool_recycle=300`: depois que o Neon suspende o servidor
  ocioso, a primeira requisição reabre a conexão em vez de falhar. A primeira consulta
  depois da pausa demora ~1 s a mais (o servidor "acorda").
- A carga inicial (`python -m backend.scripts.carga_inicial`) usa `COPY` no Postgres para
  as vendas.
- A URL tem a senha do banco: só no `.env` (fora do git), nunca no código ou em commits.
- O `PRAGMA journal_mode=WAL` do ADR-005 continua valendo apenas para o SQLite local.
