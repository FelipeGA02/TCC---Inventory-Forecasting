# ADR-005: SQLite como Banco de Dados

**Status**: Aceito  
**Data**: 2026-07-28  
**Autores**: Daniel Nunes da Silva, Felipe Gurgel Araújo

---

## Contexto

O sistema precisa persistir: dados de vendas históricos, artefatos de modelo (metadados),
usuários, métricas de avaliação e logs de retrain. O banco precisa funcionar no servidor
local da empresa sem administração adicional.

Opções avaliadas:
- SQLite (arquivo local)
- PostgreSQL (servidor dedicado)
- MySQL / MariaDB

## Decisão

**SQLite** via SQLAlchemy 2.0 com WAL mode habilitado.

## Justificativa

**Carga esperada**:
- 1–5 usuários simultâneos.
- Operação mais pesada: upload CSV (~2000 linhas) uma vez por semana.
- Retrain automático: segunda-feira 02:00, sem usuários ativos.
- Queries de leitura: forecast 3 meses, alertas, simulação — todas <100ms com índice.

**Por que não PostgreSQL**:
- Exige instalação e administração de servidor RDBMS adicional.
- A empresa não tem DBA; PostgreSQL adiciona complexidade desnecessária pós-TCC.
- Para a carga descrita, SQLite com WAL é equivalente em performance.

**WAL mode**:
- `PRAGMA journal_mode=WAL` permite leituras concorrentes enquanto uma escrita ocorre.
- Elimina o único risco real do SQLite para este perfil: um retrain escrevendo enquanto
  um usuário lê o dashboard.

**Portabilidade**:
- Zero configuração de servidor — deploy é `git clone` + `pip install` + `uvicorn`.
- Backup: copiar `floricultura.db` é suficiente.

## Limites conhecidos

- Não suporta múltiplas escritas simultâneas de alta frequência (>100 writes/s).
- Se o número de usuários crescer para >20 ou a frequência de upload aumentar, migrar
  para PostgreSQL via Alembic é viável sem mudança no domínio (SQLAlchemy abstrai o dialeto).

## Consequências

- `backend/infra/database.py` configura `engine` com `connect_args={"check_same_thread": False}` e `PRAGMA journal_mode=WAL`.
- Schema gerenciado por Alembic com migrações versionadas.
- `floricultura.db` fica em `data/` (fora do `backend/`), excluído do `.gitignore`.
