# P11: tenant preso à conexão certa

Este projeto mostra um vazamento que pode acontecer quando várias organizações usam o
mesmo pool de conexões PostgreSQL. A correção limita o tenant à transação e usa Row
Level Security (RLS) para filtrar as linhas no próprio banco. A fronteira segura também
remove um valor de sessão deixado por código antigo.

## Como o programa funciona

Duas organizações possuem documentos na mesma tabela. A aplicação consulta
`documents` sem escrever `WHERE tenant_id = ...`. Uma política RLS lê o tenant ativo e
decide quais linhas a role da aplicação pode acessar.

```text
requisição -> conexão retirada do pool -> definir tenant -> SELECT sem filtro
                       |                                  |
                       +---------- RLS no banco ----------+
```

O pool possui uma única conexão para tornar a reutilização visível pelo mesmo
`pg_backend_pid()`.

## A falha reproduzida

A versão insegura define `app.tenant_id` no escopo da sessão. O commit termina a
transação, mas não apaga esse valor. Quando a conexão volta ao pool, a próxima
requisição pode herdar o tenant anterior.

```sql
SELECT set_config('app.tenant_id', 'tenant-a', false);
```

O terceiro argumento `false` equivale ao escopo da sessão. No experimento, uma
requisição de Aurora devolve a conexão. Uma requisição seguinte esquece de configurar
o contexto e enxerga os documentos de Aurora.

## A correção

A versão segura mantém a conexão reservada, limpa um possível valor de sessão e só
então abre a transação da requisição com o equivalente a `SET LOCAL`:

```sql
SELECT set_config('app.tenant_id', '', false);
COMMIT;

BEGIN;
SELECT set_config('app.tenant_id', 'tenant-a', true);
SELECT title FROM documents ORDER BY title;
COMMIT;
```

Essa limpeza inicial importa durante uma migração. `SET LOCAL` sozinho restaura o valor
de sessão anterior ao terminar. Depois que a base da sessão está vazia, o terceiro
argumento `true` limita o novo tenant à transação atual. Commit ou rollback remove esse
valor. Uma consulta posterior sem tenant continua sem filtro na aplicação, mas a RLS
retorna zero linhas.

O código usa `psycopg_pool.ConnectionPool` para administrar a conexão e transações do
Psycopg 3 para delimitar o contexto. O mecanismo importante permanece explícito nas
duas chamadas a `set_config`.

## Por que a role importa

RLS significa segurança em nível de linha. Ela aplica uma política a cada linha antes
de a role acessar o resultado. A role `tenant_app` é criada sem `SUPERUSER` e sem
`BYPASSRLS`. A tabela também usa `FORCE ROW LEVEL SECURITY`.

Isso evita uma prova enganosa. Uma role privilegiada poderia ignorar a política mesmo
com o SQL correto.

## Para que isso serve em produção

Um backend multi-tenant costuma reutilizar poucas conexões entre muitas requisições. Se
o tenant ficar preso à sessão, um caminho de erro ou uma inicialização esquecida pode
entregar dados de outra organização.

O padrão seguro mantém estas ações enquanto possui exclusivamente a mesma conexão:

1. retirar uma conexão do pool;
2. limpar e confirmar qualquer contexto de sessão legado;
3. iniciar a transação da requisição;
4. definir o tenant com `SET LOCAL`;
5. executar todas as consultas;
6. fazer commit ou rollback antes de devolver a conexão.

A RLS funciona como uma última barreira. A aplicação ainda deve autenticar o usuário e
escolher o tenant correto.

## Como executar

Suba o PostgreSQL pinado na porta local `55441`:

```bash
docker compose up -d --wait
```

Instale e valide o projeto:

```bash
uv sync --locked
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
```

Execute a comparação:

```bash
uv run python scripts/run_experiment.py
```

O script reaplica o SQL atual em um banco descartável e grava a própria saída em
`evidence/result.txt`. Isso evita validar por engano um schema antigo preservado no
volume.

Remova o banco descartável quando terminar:

```bash
docker compose down -v
```

## Resultado observado

**Medido:** a configuração de sessão permaneceu na conexão reutilizada e expôs os
documentos de Aurora para a chamada seguinte sem contexto. A fronteira segura recebeu
essa mesma conexão contaminada, limpou o legado e usou `SET LOCAL`. Depois de commit e
de rollback, a conexão voltou sem tenant ativo. A consulta sem contexto retornou zero
linhas, e a transação de Boreal enxergou somente o próprio documento.

O resultado completo está em `evidence/result.txt`.

## Uso de RLS x uso de WHERE

As duas abordagens usam a coluna `tenant_id`, mas aplicam a proteção em lugares
diferentes.

| Abordagem | Vantagens | Limites |
| --- | --- | --- |
| `WHERE tenant_id = ...` | deixa o filtro visível no código, facilita entender a consulta e permite passar o tenant como parâmetro explícito | um endpoint, worker ou script pode esquecer o filtro e acessar linhas de outros tenants |
| RLS | aplica a regra no PostgreSQL para toda consulta feita pela role protegida e também bloqueia escritas em outro tenant | exige contexto correto na conexão, roles sem `BYPASSRLS` e testes das políticas |

As abordagens não são concorrentes. Em produção, a aplicação pode manter
`WHERE tenant_id = ...` para expressar a intenção da consulta e usar RLS como última
barreira. O backend autentica o usuário, resolve o tenant permitido e configura esse
valor na transação. O banco não decide sozinho a qual organização o usuário pertence.

## Limite do projeto

O laboratório usa PostgreSQL local, uma conexão e duas organizações sintéticas. Ele
não mede concorrência, PgBouncer, failover nem custo da política em uma tabela grande.
Uma aplicação real também precisa impedir que entrada externa escolha livremente o
tenant, revisar privilégios de migrations e testar toda nova tabela multi-tenant. A
transação curta usada para limpar legado também tem custo que este cenário não mede.

## Resumo da ópera

Não coloque o tenant no escopo permanente de uma conexão que volta ao pool. Abra uma
transação, use `SET LOCAL` e deixe a RLS negar consultas sem contexto. A role da
aplicação precisa continuar sem privilégios capazes de ignorar essa proteção.
