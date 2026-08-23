# ADR-002: Monolito Modular como Padrão Arquitetural

**Status**: Aceito  
**Data**: 2026-07-28  
**Autores**: Daniel Nunes da Silva, Felipe Gurgel Araújo

---

## Contexto

A equipe precisa decidir entre monolito modular, microserviços ou arquitetura serverless
para o backend do sistema. O sistema terá 1–5 usuários simultâneos, rodará em servidor
local da empresa e precisa ser mantido por equipe pequena após a entrega do TCC.

## Decisão

**Monolito Modular** com separação interna por camadas (Clean Architecture):
Apresentação → Aplicação → Domínio → Infraestrutura.

Um único processo FastAPI com módulos internos bem delimitados.

## Justificativa

**Por que não microserviços**:
- Volume de 1–5 usuários não justifica a complexidade operacional de múltiplos serviços.
- A equipe de manutenção pós-TCC é pequena — overhead de Docker Compose, service discovery
  e comunicação inter-serviço seria prejudicial.
- Latência de comunicação intra-processo é zero; entre serviços via HTTP adiciona overhead
  sem benefício para o volume atual.

**Por que monolito modular e não monolito simples**:
- Separação de camadas garante que o domínio SARIMAX seja testável sem FastAPI ou SQLite.
- Módulos `domain/etl/`, `domain/features/`, `domain/models/` podem ser extraídos para
  biblioteca independente no futuro sem refatoração maior.
- `backend/auth/` é isolado — substituível por OAuth2 em versão futura sem impactar o domínio.

## Estrutura de Camadas

```
Apresentação  (api/)        ← HTTP, WebSocket, validação de entrada
Aplicação     (services/)   ← orquestração de casos de uso
Domínio       (domain/)     ← lógica pura, sem I/O, testável em isolamento
Infraestrutura (infra/)     ← SQLite, filesystem, APScheduler
```

**Regra de dependência**: camadas só dependem das camadas abaixo. Domínio não importa nada acima.

## Consequências

- Deploy simples: `uvicorn backend.main:app`.
- Retrain semanal roda in-process via APScheduler — não bloqueia o dashboard.
- Se o volume de usuários crescer significativamente (>50 simultâneos), extração do
  pipeline ML para worker separado é possível sem reescrever o domínio.
