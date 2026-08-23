# ADR-006: APScheduler In-Process vs Celery para Retrain Semanal

**Status**: Aceito  
**Data**: 2026-07-28  
**Autores**: Daniel Nunes da Silva, Felipe Gurgel Araújo

---

## Contexto

O sistema precisa executar o pipeline de retrain automaticamente toda segunda-feira às 02:00.
A tarefa demora ~3 min/produto × 10 produtos = ~30 minutos no total. Durante o retrain, o
dashboard continua acessível (lê modelos do ciclo anterior até o novo ciclo estar completo).

Opções avaliadas:
- APScheduler (in-process, embutido no FastAPI)
- Celery + Redis / RabbitMQ
- Cron do sistema operacional (Windows Task Scheduler / crontab)

## Decisão

**APScheduler 3.x** in-process, embutido no processo FastAPI como `BackgroundScheduler`.

## Justificativa

**Por que não Celery**:
- Celery requer broker separado (Redis ou RabbitMQ) — infraestrutura adicional para tarefa única.
- A empresa não tem administrador de infraestrutura; dois processos adicionais (worker + broker)
  aumentam o risco operacional pós-TCC.
- Celery é justificado quando há múltiplas filas, retries com backoff e tarefas de alta frequência
  — nenhum desses casos se aplica aqui (1 tarefa, 1 vez por semana).

**Por que não cron do OS**:
- Acoplamento ao sistema operacional — a configuração de deploy mudaria entre Windows (servidor
  atual) e Linux (servidor futuro possível).
- Sem visibilidade no dashboard: o log do retrain não seria facilmente consultável pela API.

**Por que APScheduler**:
- Zero dependência externa — `pip install apscheduler`.
- `BackgroundScheduler` roda em thread separada dentro do processo, sem bloquear o event loop.
- Jobs e status de último run ficam disponíveis via API (`GET /api/v1/models/status`).
- Simples de configurar com `CronTrigger(day_of_week='mon', hour=2, minute=0)`.

## Integração

```python
# backend/infra/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler()
scheduler.add_job(retrain_all_products, CronTrigger(day_of_week='mon', hour=2))
```

O scheduler é iniciado no `lifespan` do FastAPI e encerrado graciosamente no shutdown.

## Consequências

- Retrain não persiste entre reinicializações do servidor durante a janela de execução.
  Se o servidor reiniciar às 02:15 com retrain em andamento, o job rodará na próxima
  segunda — impacto: dashboard usa modelos da semana anterior por mais 7 dias.
- Retrain manual disponível via `POST /api/v1/models/retrain` (role: admin) para mitigar.
- Se o retrain demorar >6h (crescimento futuro do catálogo), APScheduler com executor
  `ThreadPoolExecutor` ou migração para Celery são os próximos passos.
