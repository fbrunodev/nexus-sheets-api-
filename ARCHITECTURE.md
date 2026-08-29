# Nexus Backend — Arquitetura

> Documento gerado por releitura completa do código em 2026-08-27.  
> Última atualização: 2026-08-28 — adicionada seção de testes E2E; cobertura de segurança marcada como automatizada.

---

## 1. Estrutura de Pastas

```
nexus-backend/
├── main.py                        # FastAPI app, CORS, routers
├── conftest.py                    # Fixture db_session (PostgreSQL nexus_test)
├── app/
│   ├── api/v1/
│   │   ├── auth.py                # POST /auth/register|login, GET /auth/me
│   │   ├── sheets.py              # CRUD de sheets + linhas + stats
│   │   ├── costs.py               # CRUD de custos e tipos de custo
│   │   ├── dashboard.py           # GET /dashboard/ — ÓRFÃO: não consumido pelo frontend
│   │   ├── operators.py           # GET|POST|DELETE /operators/
│   │   ├── admin.py               # GET|POST /admin/keys
│   │   ├── platforms.py           # GET|POST|DELETE /platforms/
│   │   └── push.py                # POST /push/subscribe|unsubscribe, GET vapid-public-key
│   ├── services/
│   │   ├── auth.py                # register_user, login_user
│   │   ├── sheet.py               # CRUD de sheets + linhas + stats agregados
│   │   ├── cost.py                # CRUD de costs e cost_types
│   │   ├── platform.py            # CRUD de platforms
│   │   ├── dashboard.py           # get_dashboard_data — ÓRFÃO: não chamado pelo frontend
│   │   ├── admin.py               # create_activation_key, list_activation_keys
│   │   ├── operator.py            # list/create/delete operators
│   │   └── push.py                # save/delete subscriptions, send_push_to_user
│   ├── repositories/
│   │   ├── sheet.py               # SheetRepository + SheetLineRepository
│   │   ├── user.py                # UserRepository + ActivationKeyRepository
│   │   └── platform.py            # PlatformRepository
│   ├── models/
│   │   ├── user.py                # User, UserRole (enum), PlanType (enum)
│   │   ├── sheet.py               # Sheet, SheetLine, SheetStatus (enum), CooperationType (enum)
│   │   ├── platform.py            # Platform
│   │   ├── cost.py                # Cost, CostType
│   │   ├── activation_key.py      # ActivationKey (importa PlanType de user.py)
│   │   └── push_subscription.py   # PushSubscription
│   ├── schemas/
│   │   ├── user.py                # UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse
│   │   ├── sheet.py               # SheetCreate, SheetUpdate, SheetResponse, SheetLineUpdate, SheetLineResponse
│   │   ├── cost.py                # CostCreate, CostResponse, CostTypeCreate, CostTypeResponse
│   │   ├── operator.py            # OperatorCreate, OperatorResponse
│   │   ├── dashboard.py           # DashboardResponse, CostSummary, MonthlyPerformance — ÓRFÃO
│   │   ├── admin.py               # ActivationKeyCreate, ActivationKeyResponse
│   │   └── platform.py            # PlatformCreate, PlatformResponse
│   ├── exceptions/
│   │   ├── sheet_exceptions.py
│   │   ├── cost_exceptions.py
│   │   ├── user_exceptions.py
│   │   └── platform_exceptions.py
│   ├── core/
│   │   ├── config.py              # Settings (pydantic-settings)
│   │   ├── database.py            # Base, get_db, engine
│   │   ├── security.py            # hash_password, verify_password, create_access_token
│   │   └── logging_config.py      # logging_config()
│   ├── auth/
│   │   └── dependencies.py        # get_current_user (JWT → User)
│   └── logs/                      # diretório de logs (runtime)
└── tests/
    ├── services/
    │   ├── test_sheet_service.py
    │   ├── test_platform_service.py
    │   └── test_user_service.py
    ├── integration/
    │   ├── test_sheet_integration.py
    │   ├── test_cost_integration.py
    │   └── test_dashboard_integration.py
    └── e2e/
        └── test_critical_flows.py  # Fluxos críticos via TestClient (HTTP real)
```

---

## 2. Fluxo de Camadas

### Padrão geral

```
Rota (api/v1/) → Service (services/) → Repository (repositories/) → DB
```

### Status por serviço

| Serviço | Usa repositório formal | Acessa DB diretamente também |
|---|---|---|
| `services/auth.py` | `UserRepository`, `ActivationKeyRepository` | Não |
| `services/sheet.py` | `SheetRepository`, `SheetLineRepository` | **Sim** — queries a `User` em `get_sheet`, `create_new_sheet`, `finish_sheet`, `get_sheets_stats` e `calc_owner_stats` |
| `services/platform.py` | `PlatformRepository` | Não |
| `services/admin.py` | `ActivationKeyRepository` (só em `create_activation_key`) | **Sim** — `list_activation_keys` faz `db.query(ActivationKey)` direto |
| `services/operator.py` | `UserRepository` (só em `create_operator`) | **Sim** — `list_operators` e `delete_operator` fazem `db.query(User)` direto |
| `services/cost.py` | Nenhum | **Sim** — todas as funções acessam `Cost`/`CostType` direto |
| `services/dashboard.py` | Nenhum | **Sim** — queries em `Sheet`/`SheetLine` direto; delega custos para `services/cost.get_cost_stats` |
| `services/push.py` | Nenhum | **Sim** — queries em `PushSubscription` direto |

### Domínios sem repositório formal

Os seguintes modelos **não têm repositório** — seus serviços acessam o banco diretamente:

- `Cost` / `CostType` → `services/cost.py`
- `PushSubscription` → `services/push.py`

---

## 3. Modelos de Domínio

### User

| Campo | Tipo | Observação |
|---|---|---|
| `id` | `str` (UUID) | PK |
| `email` | `str(255)` | unique |
| `name` | `str(255)` | nullable |
| `password_hash` | `str(255)` | |
| `role` | `UserRole` | ADMIN / SUPERVISOR / OPERADOR / USER |
| `is_active` | `bool` | default False |
| `plan_type` | `PlanType` | LIFETIME / MONTHLY / TRIAL |
| `plan_expires_at` | `datetime` | coluna DB = `plan_expiration`; None = sem expiração |
| `created_at` | `datetime` | |
| `last_login` | `datetime` | nullable; persistido no login via `db.commit()` |
| `owner_id` | `str` FK → `users.id` | OPERADOR aponta para seu admin/supervisor |

### Sheet

| Campo | Tipo | Observação |
|---|---|---|
| `id` | `str` (UUID) | PK |
| `name` | `str(255)` | |
| `goal` | `int` | meta numérica |
| `cooperation_type` | `CooperationType` | META / BAU / RECARGA |
| `owner_id` | `str` FK → `users.id` | |
| `operator_id` | `str` FK → `users.id` | nullable |
| `status` | `SheetStatus` | NOT_STARTED → IN_PROGRESS → FINISHED |
| `salary` | `Numeric(10,2)` | |
| `is_deleted` | `bool` | soft delete |
| `platform_id` | `str` FK → `platforms.id` | nullable |
| `lines` | relationship | `SheetLine[]`, ordered by `line_number`, lazy="select" |

### SheetLine

| Campo | Tipo | Observação |
|---|---|---|
| `id` | `str` (UUID) | PK |
| `sheet_id` | `str` FK → `sheets.id` | |
| `line_number` | `int` | ordenação; sem UNIQUE constraint |
| `deposit` | `Numeric(10,2)` | |
| `withdrawal` | `Numeric(10,2)` | |
| `chest` | `Numeric(10,2)` | |
| `bonus` | `Numeric(10,2)` | bônus de plataforma |
| `result` | `Numeric(10,2)` | derivado: `withdrawal + chest + bonus - deposit` |

### Platform

| Campo | Tipo | Observação |
|---|---|---|
| `id` | `str` (UUID) | PK |
| `name` | `str(100)` | unique |

### Cost / CostType

| Modelo | Campos relevantes |
|---|---|
| `CostType` | `id`, `name` (unique), `created_by` FK → `users.id` |
| `Cost` | `id`, `cost_type_id` FK, `owner_id` FK, `value`, `month`, `year`, `description` |

`month` e `year` são armazenados explicitamente para permitir lançamentos retroativos.

### ActivationKey

| Campo | Tipo | Observação |
|---|---|---|
| `key` | `str(50)` | formato `NX-XXXX-XXXX-XXXX` |
| `type` | `PlanType` | reutiliza o enum de `user.py` |
| `expires_at` | `datetime` | nullable (LIFETIME = None) |
| `is_used` | `bool` | |
| `used_by` | `str` FK → `users.id` | nullable |

### PushSubscription

| Campo | Tipo | Observação |
|---|---|---|
| `owner_id` | `str` FK → `users.id` | |
| `endpoint` | `Text` | unique; chave de deduplicação |
| `p256dh` | `Text` | |
| `auth` | `Text` | |

---

## 4. Endpoints — Mapeamento Completo

> `⚠ órfão` = rota funcional no backend, mas não chamada pelo frontend em nenhum componente.

| Método | Rota | Handler | Serviço |
|---|---|---|---|
| POST | `/api/v1/auth/register` | `auth.register` | `auth.register_user` |
| POST | `/api/v1/auth/login` | `auth.login` | `auth.login_user` |
| GET | `/api/v1/auth/me` | `auth.me` | — (dependency) |
| GET | `/api/v1/sheets/` | `sheets.get_sheets` | `sheet.list_sheets` + `count_sheets` |
| GET | `/api/v1/sheets/stats` | `sheets.get_stats` | `sheet.get_sheets_stats` |
| GET | `/api/v1/sheets/operator-sheets` | `sheets.get_operator_sheets` | query direta no router |
| POST | `/api/v1/sheets/` | `sheets.create_sheet` | `sheet.create_new_sheet` |
| GET | `/api/v1/sheets/{id}` | `sheets.get_sheet_by_id` | `sheet.get_sheet` |
| PATCH | `/api/v1/sheets/{id}` | `sheets.update_sheet` | `sheet.update_existing_sheet` |
| POST | `/api/v1/sheets/{id}/finish` | `sheets.finish_sheet_endpoint` | `sheet.finish_sheet` |
| DELETE | `/api/v1/sheets/{id}` | `sheets.delete_sheet_endpoint` | `sheet.delete_sheet` |
| PATCH | `/api/v1/sheets/{id}/lines/{lid}` | `sheets.update_line_endpoint` | `sheet.update_line` |
| POST | `/api/v1/sheets/{id}/lines` | `sheets.add_lines_endpoint` | `sheet.add_lines` |
| DELETE | `/api/v1/sheets/{id}/lines/{lid}` | `sheets.remove_line_endpoint` | `sheet.remove_line` |
| POST | `/api/v1/sheets/{id}/clear` | `sheets.clear_lines_endpoint` | `sheet.clear_all_lines` |
| GET | `/api/v1/dashboard/` ⚠ órfão | `dashboard.dashboard` | `dashboard.get_dashboard_data` |
| GET | `/api/v1/operators/` | `operators.get_operators` | `operator.list_operators` |
| POST | `/api/v1/operators/` | `operators.create_new_operator` | `operator.create_operator` |
| DELETE | `/api/v1/operators/{id}` | `operators.delete_operator_endpoint` | `operator.delete_operator` |
| GET | `/api/v1/costs/types` | `costs.get_cost_types` | `cost.list_cost_types` |
| POST | `/api/v1/costs/types` | `costs.create_cost_type_endpoint` | `cost.create_cost_type` |
| DELETE | `/api/v1/costs/types/{id}` | `costs.delete_cost_type_endpoint` | `cost.delete_cost_type` |
| GET | `/api/v1/costs/` | `costs.get_costs` | `cost.list_costs` |
| POST | `/api/v1/costs/` | `costs.create_cost_endpoint` | `cost.add_cost_to_a_user` |
| DELETE | `/api/v1/costs/{id}` | `costs.delete_cost_endpoint` | `cost.delete_cost` |
| GET | `/api/v1/costs/stats` | `costs.get_cost_stats_endpoint` | `cost.get_cost_stats` |
| GET | `/api/v1/platforms/` | `platforms.get_platforms` | `platform.list_platforms` |
| POST | `/api/v1/platforms/` | `platforms.create_platform_endpoint` | `platform.create_new_platform` |
| DELETE | `/api/v1/platforms/{id}` | `platforms.delete_platform_endpoint` | `platform.remove_platform` |
| GET | `/api/v1/admin/keys` | `admin.get_keys` | `admin.list_activation_keys` |
| POST | `/api/v1/admin/keys` | `admin.create_key` | `admin.create_activation_key` |
| POST | `/api/v1/push/subscribe` | `push.subscribe` | `push.save_subscription` |
| POST | `/api/v1/push/unsubscribe` | `push.unsubscribe` | `push.delete_subscription` |
| GET | `/api/v1/push/vapid-public-key` | `push.get_vapid_public_key` | — |
| GET/HEAD | `/health` | `health_check` | — |

### Contexto do endpoint órfão

A tela `/dashboard` do frontend **não chama** `GET /api/v1/dashboard/`. Ela monta o dashboard com três chamadas independentes:

| Dado exibido | Endpoint real usado | Observação |
|---|---|---|
| Card "Lucro Total" + contadores | `GET /sheets/stats?period=…` | Inclui salary, bonus e desconta custos |
| Gráfico de pizza de custos | `GET /costs/stats?period=…` | Retorna tipos reais do usuário, sem hardcoding |
| Gráfico de linha + tabela | `GET /sheets/?limit=10&period=…` | Resultado calculado client-side |

O tipo TypeScript `DashboardData` (em `nexus-frontend/types/index.ts`) também existe mas não é referenciado por nenhum componente.

---

## 5. Exceções de Domínio

### `exceptions/sheet_exceptions.py`

| Classe | Motivo | HTTP na rota |
|---|---|---|
| `SheetNotFoundException` | Planilha não existe ou não pertence ao owner | 404 |
| `SheetAlreadyFinishedException` | Tentativa de editar planilha com status FINISHED | 403 |
| `SheetLineNotFoundException` | Linha não existe no sheet requisitado | 404 |

### `exceptions/cost_exceptions.py`

| Classe | Motivo | HTTP na rota |
|---|---|---|
| `CostAlreadyExistsException` | `CostType` com mesmo `name` já existe | 409 (POST /costs/types) |
| `CostNotFoundException` | `Cost` não encontrado por `id + owner_id` | 404 (DELETE /costs/{id}) |
| `CostTypeNotFoundException` | `CostType` não encontrado por `id` | 404 (DELETE /costs/types/{id}) e 400 (POST /costs/) |

### `exceptions/user_exceptions.py`

| Classe | Motivo | HTTP na rota |
|---|---|---|
| `UserInvalidCredentialsException` | Email ou senha incorretos | 401 (POST /auth/login) |
| `UserInactiveAccountException` | `is_active = False` | 403 (POST /auth/login) |
| `UserExpiredPlanException` | `plan_expires_at` no passado | 403 (POST /auth/login) |
| `UserEmailAlreadyExistsException` | Email duplicado | 409 (POST /auth/register e POST /operators/) |
| `OperatorNotFoundException` | Operador não existe ou não pertence ao owner | 404 (DELETE /operators/{id}) |
| `InvalidKeyException` | `activation_key` não existe no banco | 404 (POST /auth/register) |
| `KeyAlreadyUsedException` | Chave já foi resgatada | 400 (POST /auth/register) |
| `KeyExpiredException` | Chave com `expires_at` no passado | 400 (POST /auth/register) |
| `ActivationKeyGenerationException` | Falha ao gerar chave única após 5 tentativas | 400 (POST /admin/keys) |

### `exceptions/platform_exceptions.py`

| Classe | Motivo | HTTP na rota |
|---|---|---|
| `PlatformNameEmptyException` | Nome da plataforma é string vazia após `.strip()` | 400 (POST /platforms/) |
| `PlatformAlreadyExistsException` | Plataforma com mesmo nome já existe | 409 (POST /platforms/) |
| `PlatformNotFoundException` | Plataforma não encontrada por `id` | 404 (DELETE /platforms/{id}) |

---

## 6. Testes E2E

### Propósito

Exercitar fluxos críticos do sistema de ponta a ponta, passando pela stack HTTP completa (roteamento, autenticação JWT, serviços, banco de dados). Diferente dos testes de integração  que testam serviços isoladamente com sessão de banco injetada os testes E2E disparam requisições HTTP reais via `TestClient` do FastAPI e validam o comportamento observável da API.

### Infraestrutura

- **Ferramenta:** `fastapi.testclient.TestClient` (ASGI síncrono, sem servidor de rede)
- **Banco:** PostgreSQL `nexus_test` (mesmo banco usado pelos testes de integração)
- **Isolamento:** `app.dependency_overrides[get_db]` substitui a dependência `get_db` pela sessão de teste; cada teste chama `Base.metadata.create_all` no início e `Base.metadata.drop_all` no `finally`, garantindo isolamento completo entre testes
- **Arquivo:** `tests/e2e/test_critical_flows.py`

### Cobertura

| Teste | Fluxo validado | Resultado esperado |
|---|---|---|
| `test_login_e2e_success` | Login com credenciais válidas | 200 + `access_token` presente na resposta |
| `test_create_sheet_with_user_authenticated` | Login → obtenção de token → criação de sheet autenticada | 201 + sheet criada com `name` correto |
| `test_trying_to_accesss_and_edit_operator_sheet` | Supervisor tenta editar sheet cujo `owner_id` é um operador vinculado; em seguida operador verifica que o dado não foi alterado | PATCH retorna 404; GET pelo operador retorna `salary == 0` |
| `test_trying_to_delete_a_sheet_from_another_user` | Supervisor tenta deletar sheet cujo `owner_id` é um operador vinculado; em seguida operador verifica que o sheet ainda existe | DELETE retorna 404; GET pelo operador retorna 200 com `id` correto |
| `test_trying_to_access_without_authorization` | Requisição sem header `Authorization` | 401 |
| `test_trying_to_access_with_an_invalid_token` | Requisição com token JWT malformado (separadores `-` em vez de `.`) | 401 |
| `test_trying_to_access_with_an_expired_token` | Requisição com token JWT expirado (`expires_delta=-1s`) | 401 |

### Papel dos testes de regressão de segurança

Os testes `test_trying_to_accesss_and_edit_operator_sheet` e `test_trying_to_delete_a_sheet_from_another_user` foram criados para fixar uma falha de segurança identificada anteriormente, em que um supervisor conseguia modificar ou deletar sheets de operadores vinculados a ele. Esses testes são testes de **regressão permanente**: qualquer mudança no serviço `sheet.py` ou na lógica de autorização das rotas que reintroduza essa brecha fará os testes falharem.

---

## 7. Cobertura de Testes

### `tests/services/` — Testes unitários (fake repositories, `db = MagicMock()`)

| Arquivo | Serviço coberto | O que é testado |
|---|---|---|
| `test_sheet_service.py` | `services/sheet.py` | `create_new_sheet`, `update_existing_sheet`, `finish_sheet`, `delete_sheet`, `add_lines`, `update_line`, `remove_line`, `clear_all_lines`, `calculate_period_filter`; exceções: `SheetNotFoundException`, `SheetAlreadyFinishedException`, `SheetLineNotFoundException` |
| `test_platform_service.py` | `services/platform.py` | `create_new_platform` (já existe, nome vazio); `remove_platform` (não encontrado) |
| `test_user_service.py` | `services/auth.py` + `services/admin.py` | `register_user` (sucesso, email duplicado, chave usada, chave inválida, chave expirada); `login_user` (sucesso, credenciais inválidas, senha errada, conta inativa, plano expirado); `create_activation_key` |

### `tests/integration/` — Testes de integração (PostgreSQL `nexus_test` real, criado e destruído pela fixture `db_session`)

| Arquivo | Serviço/Repositório coberto | O que é testado |
|---|---|---|
| `test_sheet_integration.py` | `SheetRepository` + `services/sheet.py` | `get_sheets_by_owner` com filtro por status; `get_sheets_by_owner` com filtro de período; `count_sheets_by_owner`; `get_sheets_stats` (agregação completa com linhas) |
| `test_cost_integration.py` | `services/cost.py` | `get_cost_stats`; `create_cost_type` (já existe); `delete_cost_type` (não encontrado); `add_cost_to_a_user` (cost_type não encontrado); `delete_cost` (não encontrado) |
| `test_dashboard_integration.py` | `services/dashboard.py` | `get_dashboard_data`: valida desconto de custos reais em `final_result` e valor correto de `costs.bot` (1 teste, caminho feliz, `period="all"`, todas as linhas com `bonus=0`) |

### `tests/e2e/` — Testes E2E (TestClient HTTP, PostgreSQL `nexus_test` real, schema recriado por teste)

| Arquivo | O que é testado |
|---|---|
| `test_critical_flows.py` | Login, criação autenticada de sheet, bloqueio de edição de sheet de operador por supervisor (**regressão de segurança**), bloqueio de deleção de sheet de operador por supervisor (**regressão de segurança**), acesso sem token (401), token malformado (401), token expirado (401) |

### Não coberto por nenhum teste

- `services/dashboard.py` — 1 teste de caminho feliz; sem cenário com `bonus > 0`, sem cobertura dos filtros de período
- `services/push.py` — zero cobertura
- `services/operator.py` — zero cobertura
- `list_costs`, `list_cost_types`, `list_platforms`, `list_operators`, `list_activation_keys`
- Fluxo de `GET /sheets/operator-sheets` (query direta no router, sem service)

---

## 8. Pendências e Decisões de Escopo

### Decisão de produto pendente

**D1 — Definir o destino do endpoint `GET /api/v1/dashboard/`**  
O endpoint existe, compila, tem service funcional e teste de integração, mas não é consumido por nenhuma parte do frontend. A interface TypeScript `DashboardData` (em `types/index.ts`) também existe sem uso. Há duas opções mutuamente exclusivas:

- **Remover:** deletar `api/v1/dashboard.py`, `services/dashboard.py`, `schemas/dashboard.py`, `test_dashboard_integration.py` e o tipo `DashboardData`. Elimina código morto e reduz superfície de manutenção.
- **Conectar:** migrar o frontend para usar este endpoint em vez das três chamadas independentes atuais. Requer resolver D2 (inconsistência do `monthly_performance`) e D3 (naming de `CostSummary`) antes de conectar.

Enquanto a decisão não for tomada, D2 e D3 abaixo têm prioridade baixa — são problemas num endpoint que ninguém usa.

### Inconsistências no endpoint órfão (impacto zero enquanto D1 não for decidido)

**D2 — `monthly_performance[].result` não inclui `chest`, `bonus` nem `salary`**  
O campo `result` por mês é calculado como `received - deposited`, enquanto `final_result` global inclui `+ chest + bonus + salary - costs`. Se o endpoint for conectado ao frontend, os dois números vão divergir visivelmente para qualquer usuário que use `chest`, `bonus` ou `salary`. Decisão de como alinhar depende da semântica desejada para o gráfico mensal (P&L bruto vs. resultado líquido).

**D3 — `CostSummary` assume nomes de categoria exatos em maiúsculas**  
`cost_map.get("PROXY", 0.0)`, `cost_map.get("SMS", 0.0)` etc. O `total_costs` é correto (soma tudo), mas o breakdown individual retorna 0 silenciosamente se o usuário nomeou seus tipos de custo de forma diferente. Se o endpoint for conectado, o breakdown de proxy/sms/bot/fintech deve ser desacoplado dos nomes, ou os nomes devem ser documentados como convenção obrigatória.

### MÉDIA prioridade

**P1 — Ausência de testes para push e operator**  
`services/push.py` e `services/operator.py` não têm nenhum teste unitário ou de integração.

### BAIXA prioridade

**P3 — Acesso direto ao banco em serviços com repositório parcial**  
`services/operator.py` (`list_operators`, `delete_operator`) e `services/admin.py` (`list_activation_keys`) acessam o banco diretamente sem repositório. `services/sheet.py` também faz queries diretas a `User` dentro de funções que usam repositórios formais. Dificulta testes unitários com fakes.

**P4 — Divergência de nomes: `plan_expires_at` (Python) vs `plan_expiration` (coluna DB)**  
O model `User` mapeia `plan_expires_at` para a coluna `plan_expiration`. É funcional, mas a divergência pode confundir ao inspecionar o schema do banco diretamente ou ao escrever migrations.

---

## 9. Decisões de Escopo

**Dashboard mostra apenas performance do dono, sem consolidar operadores**  
A tela `/dashboard` do frontend filtra por `owner_id` do usuário autenticado e não itera sobre operadores vinculados. Decisão consciente: o dashboard é uma visão pessoal. A visão consolidada de operadores é responsabilidade da tela de operadores (a implementar futuramente).

Contraste com `GET /sheets/stats`, que agrega os resultados dos operadores vinculados ao owner. Os dois endpoints têm propósitos diferentes por design.
