# ADR-007: openapi-typescript-codegen para Cliente TypeScript Gerado

**Status**: Aceito  
**Data**: 2026-07-28  
**Autores**: Daniel Nunes da Silva, Felipe Gurgel Araújo

---

## Contexto

O frontend React precisa consumir 13 endpoints do backend FastAPI. A escolha é entre
escrever o cliente HTTP manualmente (axios/fetch com tipos definidos à mão) ou gerar
automaticamente a partir do `openapi.yaml`.

Opções avaliadas:
- Cliente manual com axios + tipos TypeScript escritos à mão
- `openapi-fetch` (geração leve, sem classes)
- `openapi-typescript-codegen` (geração completa com services + models)
- `orval` (alternativa moderna baseada em React Query)

## Decisão

**`openapi-typescript-codegen`** (pacote `@openapitools/openapi-generator-cli` ou
equivalente `openapi-typescript-codegen@0.26`) com output em `app-react/src/api/`.

## Justificativa

**Por que não cliente manual**:
- 13 endpoints com 17 schemas — manter tipos sincronizados manualmente é fonte de bugs.
- Qualquer mudança no backend exige atualização manual no frontend — violação do princípio
  "openapi.yaml como fonte da verdade".

**Por que não `openapi-fetch`**:
- Gera apenas tipos, não wrappers de chamada — reduz mas não elimina código manual.
- `openapi-typescript-codegen` gera `services/` completos com autenticação Bearer embutida.

**Por que `openapi-typescript-codegen`**:
- Gera `ApiClient`, `AuthService`, `ForecastService`, etc. com tipos completos.
- Configuração Bearer token: `OpenAPI.TOKEN = accessToken` — uma linha.
- Quando `openapi.yaml` muda, basta `npm run codegen` — o TypeScript compiler aponta
  qualquer divergência no código do frontend.

**Por que não `orval`**:
- Orval gera hooks React Query — boa escolha para projetos que já usam React Query.
- Para este projeto o cliente simples basta; introduzir React Query adiciona dependência.

## Setup

```bash
# Instalação (uma vez)
npm install --save-dev openapi-typescript-codegen

# package.json script
"codegen": "openapi --input ../ia-predictor/openapi.yaml --output src/api --client axios"

# Uso após mudanças no backend
npm run codegen
```

## Output gerado

```
app-react/src/api/
├── core/
│   ├── ApiError.ts
│   ├── OpenAPI.ts          ← configuração do Bearer token
│   └── request.ts
├── models/
│   ├── ForecastResponse.ts
│   ├── AlertItem.ts
│   └── ... (17 schemas)
└── services/
    ├── AuthService.ts
    ├── ForecastService.ts
    ├── AlertsService.ts
    └── ... (1 por grupo de endpoints)
```

## Contrato de Consistência

`openapi.yaml` é o **único** lugar onde a API é definida. Regra: qualquer endpoint novo
ou mudança de schema começa em `openapi.yaml`, depois `npm run codegen`, depois implementação
backend + frontend. Nunca o contrário.

## Consequências

- `src/api/` é diretório gerado — adicionado ao `.gitignore` é opcional (pode ser commitado
  para facilitar revisão de PR). Decisão: commitar para rastreabilidade.
- Versão do pacote fixada (`0.26.x`) para evitar mudanças de gerador quebrarem o build.
- Se o backend migrar para GraphQL no futuro, substituir por `graphql-codegen`.
