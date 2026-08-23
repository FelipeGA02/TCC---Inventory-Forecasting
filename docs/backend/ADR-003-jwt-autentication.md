# ADR-003: JWT com Perfis admin/viewer para Autenticação

**Status**: Aceito  
**Data**: 2026-07-28  
**Autores**: Daniel Nunes da Silva, Felipe Gurgel Araújo

---

## Contexto

O sistema expõe dados operacionais sensíveis (volume de vendas, estratégias de compra)
e permite ações destrutivas (upload de dados, disparo de retrain). O artigo TCC define
RNF-04: controle de acesso por perfil de usuário em conformidade com LGPD.

Opções avaliadas:
- Sem autenticação (API aberta na rede interna)
- API Key estática no `.env`
- JWT com perfis de usuário
- OAuth2 (Google, Microsoft)

## Decisão

**JWT (HS256)** com dois perfis: `admin` e `viewer`.  
Biblioteca: `python-jose[cryptography]` para tokens, `passlib[bcrypt]` para senhas.

## Justificativa

**Por que não sem autenticação**:
- Dados de volume de vendas e estratégias de compra são confidenciais.
- Upload sem controle poderia corromper a base histórica.
- LGPD exige controle de acesso mesmo em sistemas internos.

**Por que não API Key**:
- Sem granularidade de perfis — impossível distinguir admin de viewer.
- Chave compartilhada por todos os usuários — sem rastreabilidade de ações individuais.

**Por que não OAuth2 externo**:
- A empresa não tem Google Workspace ou Microsoft 365.
- Adiciona dependência de serviço externo desnecessária para 2–5 usuários.

**Por que JWT**:
- Stateless: sem session store adicional.
- Perfis codificados no token: `{ "sub": "email", "role": "admin" }`.
- Access token curto (8h) + refresh token longo (7d) — equilíbrio segurança/usabilidade.
- Padrão da indústria, bem suportado em FastAPI e React.

## Perfis

| Perfil | Permissões |
| --- | --- |
| `admin` | upload, retrain, todas as leituras |
| `viewer` | somente leituras (forecast, alerts, simulation, export) |

## LGPD

A API **nunca** retorna `cliente_nome`, `cliente_cod` ou qualquer dado pessoal de clientes.
Apenas dados agregados por produto são expostos. Isso está garantido nos schemas Pydantic
de resposta — campos de cliente estão ausentes de todos os response models.

## Consequências

- `backend/auth/seed_users.py` cria usuários iniciais a partir do `.env` no primeiro boot.
- Mudança de senha requer acesso ao servidor (sem fluxo de "esqueci a senha" no MVP).
- Tokens não são revogáveis antes da expiração (sem blacklist) — aceitável para 8h de duração.
- Expansão para múltiplos usuários ou OAuth2 não requer mudança no domínio.
