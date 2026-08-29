# nexus-sheets-api

Backend da aplicação Nexus Sheets — sistema de gerenciamento de planilhas para operadores de apostas. Controla depósitos, saques, metas e custos por operador, com hierarquia de usuários (admin / supervisor / operador).

## Stack

- Python 3.13
- FastAPI + Uvicorn
- SQLAlchemy 2 + Alembic
- PostgreSQL
- Pydantic v2 + pydantic-settings
- python-jose (JWT)
- bcrypt
- uv

## Destaques técnicos

**Arquitetura em camadas** — cada requisição passa por rota → service → repositório → banco. Lógica de negócio fica nos services, queries ficam nos repositórios, rotas só traduzem HTTP.

**Suíte de testes em três camadas**:
- Unitários: services isolados com repositórios falsos e `db = MagicMock()`, sem dependência de banco
- Integração: services e repositórios rodando contra PostgreSQL real, com schema criado e destruído por fixture a cada teste
- E2E: fluxos HTTP completos via `TestClient` do FastAPI com banco real; inclui testes de regressão permanente de controle de acesso — garantem que um usuário não consegue modificar ou deletar recursos que pertencem a outro

**CI/CD** — GitHub Actions roda `mypy` e `pytest` completo em todo push e PR para `main`. O deploy no Render só é disparado se todos os checks passarem.

## Arquitetura

```
nexus-backend/
├── main.py              # FastAPI app, CORS, registro de routers
├── alembic/             # migrations
├── app/
│   ├── api/v1/          # rotas: auth, sheets, costs, operators, platforms, admin, push
│   ├── services/        # lógica de negócio
│   ├── repositories/    # encapsula queries ao banco
│   ├── models/          # modelos SQLAlchemy
│   ├── schemas/         # schemas Pydantic (request/response)
│   ├── exceptions/      # exceções de domínio por módulo
│   ├── core/            # config, database, security, logging
│   └── auth/            # dependência get_current_user (JWT → User)
└── tests/
    ├── services/        # unitários (sem banco)
    ├── integration/     # integração com banco real
    └── e2e/             # fluxos HTTP completos
```

Fluxo de uma requisição: `rota → service → repositório → banco`

## Como rodar localmente

**1. Instalar dependências**

```bash
uv sync
```

**2. Configurar variáveis de ambiente**

```bash
cp .env.example .env
```

Preencha no `.env`:

```
DATABASE_URL=postgresql://user:senha@localhost:5432/nexus_sheets
SECRET_KEY=qualquer_string_longa_aleatoria
DEBUG=True
```

As variáveis `VAPID_*` são necessárias apenas para push notifications — o resto da API funciona sem elas.

**3. Rodar as migrations**

```bash
uv run alembic upgrade head
```

**4. Subir o servidor**

```bash
uv run uvicorn main:app --reload
```

API disponível em `http://localhost:8000`. Documentação em `/docs`.

## Testes

Os testes usam um banco separado, com a conexão hardcoded em `conftest.py`:

```
postgresql://postgres:postgres@localhost:5432/nexus_test
```

Crie esse banco antes de rodar os testes:

```sql
CREATE DATABASE nexus_test;
```

O `SECRET_KEY` precisa estar no `.env` ou como variável de ambiente — os testes E2E precisam dele para assinar tokens JWT.

O schema é criado e destruído automaticamente por fixture — não precisa rodar migrations no banco de teste.

```bash
# Unitários (sem banco)
uv run pytest tests/services/ -v

# Integração
uv run pytest tests/integration/ -v

# E2E
uv run pytest tests/e2e/ -v

# Tudo
uv run pytest -v
```

Type checking:

```bash
uv run mypy .
```
