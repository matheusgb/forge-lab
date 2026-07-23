# P10: Clínica do plano de consulta

Este projeto responde a uma pergunta prática: como saber se uma consulta precisa de um
índice, de outra projeção ou de uma mudança no acesso da aplicação?

A resposta não parte de uma regra pronta. O PostgreSQL executa o mesmo acesso em três
condições, e o projeto guarda o plano escolhido em cada uma. Depois, a aplicação busca
o mesmo resultado com N+1 consultas e com um único `JOIN`.

## Como o programa funciona

O experimento cria um PostgreSQL descartável e insere um cenário determinístico com
120 mil pedidos. Um tenant possui 120 pedidos pendentes. A consulta procura os 50 mais
recentes. O script aceita somente o banco local reservado na porta `55440`, pois recria
o schema `query_clinic` do zero.

```text
mesma consulta
    |
    +--> sem índice
    +--> índice apenas em status
    +--> índice em tenant, status e created_at
    |
    v
EXPLAIN (ANALYZE, BUFFERS)
    |
    v
scan, filtros, ordenação, linhas e páginas acessadas
```

O script também executa duas formas de carregar pedido e cliente:

```text
N+1: 1 consulta de pedidos + 1 consulta por cliente
JOIN: 1 consulta com somente as colunas necessárias
```

O resultado lógico precisa ser igual. O número de consultas e o volume serializado
ficam visíveis para que tempo isolado não seja a única evidência.

O cenário desativa o paralelismo do plano para deixar a escolha de scan e índice mais
fácil de ler. Essa é uma premissa didática, não uma recomendação para produção.

## O que cada índice demonstra

Sem um índice útil, o PostgreSQL lê a tabela e ordena os candidatos. O plano mostra um
`Seq Scan`, que é a leitura sequencial da tabela.

O índice apenas em `status` encontra pedidos pendentes, mas ainda precisa descartar os
outros tenants e ordenar por `created_at`. Ele ajuda uma parte do filtro, mas não atende
o acesso completo.

O índice alinhado usa esta ordem:

```sql
(tenant_id, status, created_at DESC)
INCLUDE (id, customer_id, total_cents)
```

As duas primeiras colunas resolvem o filtro. A terceira entrega a ordem pedida. As
colunas em `INCLUDE` cobrem a projeção sem participar da busca. Quando as páginas estão
visíveis para o PostgreSQL, o plano pode usar `Index Only Scan` e evitar buscar a linha
na tabela.

## Por que um sequential scan pode estar certo

O experimento mantém um índice em `status` e consulta todos os pedidos concluídos. Eles
representam 98% da tabela sintética. Nesse caso, visitar quase toda a tabela por meio do
índice tende a custar mais do que ler suas páginas em sequência.

Por isso, `Seq Scan` não significa automaticamente ausência de otimização. O acesso é
legítimo quando a consulta precisa de uma parte grande da tabela. O plano e a
seletividade precisam ser lidos juntos.

## N+1 e projeção

N+1 acontece quando a aplicação carrega uma lista e depois executa uma nova consulta
para cada item. Com 20 pedidos, o cenário faz 21 consultas. O `JOIN` devolve o mesmo
resultado em uma consulta.

O projeto também compara `SELECT o.*, c.*` com a projeção de quatro campos usados pelo
resultado. O tamanho mostrado é o número de bytes da serialização JSON local. Ele serve
para provar que campos largos chegaram à aplicação, mas não mede bytes exatos do
protocolo PostgreSQL.

Em produção, N+1 acrescenta viagens pela rede, trabalho no pool e carga no banco. Uma
execução local pode esconder esse custo por ter latência muito baixa. Por isso, o
número de consultas é a evidência principal deste caso.

## Como executar

Instale o ambiente:

```bash
uv sync --locked
```

Inicie o PostgreSQL 17.5 na porta local `55440`:

```bash
docker compose up -d --wait
```

Execute o experimento:

```bash
uv run python scripts/run_experiment.py
```

Execute as verificações:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
P10_RUN_INTEGRATION=1 uv run pytest -m integration
```

Remova o banco descartável quando terminar:

```bash
docker compose down --volumes
```

## Evidências geradas

O experimento grava o resumo em `evidence/result.txt`. Cada plano fica em duas formas
na pasta `evidence/plans/`: texto curto para leitura e JSON com os campos estruturados
usados pelo experimento.

As evidências incluem:

- o tipo de scan escolhido em cada cenário;
- condição do índice e linhas removidas pelo filtro;
- buffers compartilhados e temporários;
- tempo de planejamento e execução;
- consultas feitas pelo N+1 e pelo `JOIN`;
- tamanho das projeções na serialização local.

## Resultado observado

**Medido:** no PostgreSQL 17.5 local, o acesso sem índice usou `Seq Scan`. O índice
apenas em `status` usou `Index Scan`, removeu 2.280 linhas de outros tenants e ainda
ordenou o resultado. O índice composto alinhado usou `Index Only Scan`, retornou 50
linhas, fez zero acessos ao heap e tocou sete páginas compartilhadas nesta execução.

A consulta que precisava de 117.600 das 120 mil linhas escolheu `Seq Scan` mesmo com o
índice de status disponível. O caso N+1 executou 21 consultas. O `JOIN` executou uma e
produziu o mesmo resultado lógico. A serialização local caiu de 10.139 bytes com a
projeção ampla para 1.179 bytes com os campos necessários.

Os tempos completos, buffers e árvores dos planos estão em `evidence/`. Eles pertencem
somente à execução registrada e podem mudar quando o experimento rodar novamente.

## Falha controlada

O índice apenas em `status` é a falha de desenho. Ele parece relacionado ao filtro, mas
não isola o tenant nem entrega a ordenação. O plano expõe o trabalho restante.

O N+1 é a falha no acesso da aplicação. O resultado continua correto, o que torna o
problema fácil de ignorar, mas a contagem cresce com o número de pedidos.

## Limite do projeto

O conjunto é sintético, roda em uma única instância e começa com cache e armazenamento
locais. Tempos mudam conforme máquina, cache, versão e configuração. O experimento não
define um índice universal nem comprova capacidade de produção. Ele também não compara
planos paralelos, porque o cenário desativa esse recurso para isolar a decisão central.

O índice também possui custo de escrita, espaço e manutenção que este projeto não mede.
Particionamento, estatísticas estendidas, concorrência, locks, réplicas e `VACUUM` sob
carga ficam fora do escopo.

## Resumo da ópera

Leia o plano antes de criar um índice. Alinhe igualdade, ordenação e projeção ao acesso
real. Aceite o sequential scan quando a consulta precisa de quase toda a tabela. Na
aplicação, conte consultas e peça apenas os campos usados, porque um resultado correto
ainda pode esconder N+1 e transferência desnecessária.
