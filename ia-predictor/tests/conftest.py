"""Deixa `training_scripts` e `backend` importáveis quando o pytest roda da raiz do repo
(`pytest ia-predictor/tests/unit/`), como está no CLAUDE.md."""
import os
import sys

_IA_PREDICTOR_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _IA_PREDICTOR_ROOT not in sys.path:
    sys.path.insert(0, _IA_PREDICTOR_ROOT)
