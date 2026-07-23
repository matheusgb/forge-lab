# P09: Schema que protege o domínio

Este projeto provoca quatro erros que a aplicação poderia deixar passar. O PostgreSQL
rejeita todos porque as regras importantes também vivem no schema.

## Como o programa funciona

Uma migration cria `tenants` e `orders`. SQLAlchemy descreve as mesmas tabelas no
código. O experimento insere um pedido válido e depois tenta gravar dados impossíveis.

```text
aplicação tenta gravar
        |
        v
PostgreSQL verifica FK, NOT NULL, CHECK e UNIQUE
        |
        +---- válido ----> commit
        |
        +---- inválido --> rejeição e rollback
```

Alembic controla a versão do schema. O experimento executa `downgrade base`,
`upgrade head`, testa as regras e repete o ciclo. Assim, a prova não depende de uma
tabela montada manualmente.

## O conceito principal

Uma constraint é uma regra que o banco verifica em toda escrita, independentemente de
qual endpoint, worker ou script enviou o comando. Este projeto usa:

- `FOREIGN KEY` para impedir pedido ligado a um tenant inexistente;
- `NOT NULL` para impedir um pedido sem identificador externo;
- `CHECK` para impedir `total_cents` igual ou menor que zero;
- `UNIQUE (tenant_id, external_id)` para impedir a mesma referência dentro do tenant.

A unicidade é composta. Dois tenants podem usar `checkout-42`, mas o mesmo tenant não
pode gravar essa referência duas vezes.

Migration é a alteração versionada do schema. O `upgrade` cria as tabelas e regras. O
`downgrade` desfaz a revisão em ordem segura, primeiro `orders` e depois `tenants`.

## Para que isso serve em produção

A validação da API melhora a mensagem de erro, mas não é a última defesa. Um worker
antigo, uma importação ou outra instância da aplicação pode ignorar essa validação.
Quando a invariante está no PostgreSQL, todas essas entradas passam pela mesma regra.

Exemplo: dois consumidores recebem o mesmo pedido ao mesmo tempo. Uma consulta prévia
feita por cada consumidor pode dizer que a referência ainda não existe. A constraint
`UNIQUE` decide no momento da escrita e permite apenas um commit.

## Como executar

Suba o PostgreSQL 17.6 pinado na porta local `55439`:

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

Os testes sem banco validam o contrato declarado. Para incluir os testes de integração:

```bash
DATABASE_URL=postgresql+psycopg://forge:forge@127.0.0.1:55439/schema_guard uv run pytest
```

Execute as migrations diretamente quando quiser observar cada direção:

```bash
DATABASE_URL=postgresql+psycopg://forge:forge@127.0.0.1:55439/schema_guard uv run alembic upgrade head
DATABASE_URL=postgresql+psycopg://forge:forge@127.0.0.1:55439/schema_guard uv run alembic downgrade base
```

O experimento apaga e recria as tabelas. Por segurança, o script aceita somente o banco
local `schema_guard`:

```bash
uv run python scripts/run_experiment.py
```

Ao terminar, remova o container e seus dados:

```bash
docker compose down -v
```

## Falhas reproduzidas

O cenário tenta inserir uma FK órfã, um valor nulo, um total impossível e uma referência
duplicada. Cada tentativa abre sua própria transação. A rejeição aborta somente aquela
escrita e permanece visível pelo tipo de erro devolvido pelo driver PostgreSQL.

## Resultado observado

**Medido:** PostgreSQL respondeu com `ForeignKeyViolation`, `NotNullViolation`,
`CheckViolation` e `UniqueViolation`. O mesmo `external_id` foi aceito para dois
tenants. O `downgrade` removeu as duas tabelas e um novo `upgrade` recriou ambas sem
correção manual.

O resultado completo fica em `evidence/result.txt`.

## Limite do projeto

O banco possui poucos registros e roda em um único container. O experimento não mede o
tempo de lock de uma migration em tabela grande, concorrência durante deploy, estratégia
de backfill nem compatibilidade entre versões da aplicação. Esses pontos exigem uma
evolução `expand-and-contract` e carga representativa.

## Resumo da ópera

Valide cedo na aplicação para orientar o usuário, mas grave as invariantes definitivas
no banco. Constraints protegem todas as rotas de escrita. Migrations tornam essa proteção
repetível, revisável e reversível.
