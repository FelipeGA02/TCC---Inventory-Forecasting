"""Injeção de dependências FastAPI compartilhadas entre routers."""
from backend.infrastructure.database import get_db  # noqa: F401 — reexportado para uso nos routers

# get_model_registry() é adicionado aqui pela camada de modelagem (backend/infrastructure/storage.py)
# assim que ModelRegistry estiver implementado — ver SPECS.md seção 9.2.
