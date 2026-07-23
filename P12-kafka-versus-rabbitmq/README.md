# P12: log ou fila

Kafka e RabbitMQ transportam mensagens, mas resolvem problemas diferentes. Este projeto
envia os mesmos eventos aos dois brokers e deixa visível como cada modelo controla
ordem, progresso e recuperação.

## Como o programa funciona

Um broker é um serviço que recebe mensagens e as entrega a outros programas. O
experimento sobe dois brokers: um Redpanda, compatível com o protocolo Kafka, e um
RabbitMQ. O script publica os mesmos seis eventos de pedidos nos dois lados.

```text
eventos de pedidos
       |
       +--> Kafka: guarda o histórico e a posição de cada grupo
       |
       +--> RabbitMQ: entrega uma tarefa e espera a confirmação
```

### Kafka passo a passo

O Kafka funciona como uma linha do tempo. Ler um evento não o remove. Cada grupo de
consumidores mantém seu próprio marcador de leitura.

```text
1. A aplicação publica um evento com a chave do pedido.

   aplicação
       |
       | evento evt-001, chave order-a
       v
   tópico de pedidos

2. A chave escolhe a partição.

   order-a ---> partição de order-a
   order-b ---> partição de order-b

3. Cada evento recebe uma posição chamada offset.

   partição de order-a

   offset 0        offset 1        offset 2
   evt-001  -----> evt-003  -----> evt-005

   partição de order-b

   offset 0        offset 1        offset 2
   evt-002  -----> evt-004  -----> evt-006

4. O grupo p12-live lê os eventos e salva uma posição em cada partição.

   order-a: evt-001 -> evt-003 -> evt-005 -> marcador no final
   order-b: evt-002 -> evt-004 -> evt-006 -> marcador no final

5. O mesmo grupo volta e continua depois do marcador.

   marcadores no final -> nenhum evento antigo

6. Um novo grupo começa com seus próprios marcadores e pode reler tudo.

   grupo p12-replay
      |
      +--> order-a: evt-001 -> evt-003 -> evt-005
      |
      +--> order-b: evt-002 -> evt-004 -> evt-006
```

O `order_id` é a chave neste projeto. Por isso, os eventos do mesmo pedido ficam na
mesma partição e preservam a sequência 1, 2 e 3. Eventos de pedidos diferentes podem
ficar em partições diferentes. O Kafka não promete uma ordem única entre todas elas.

### RabbitMQ passo a passo

O RabbitMQ funciona como uma fila de tarefas. A mensagem continua pendente até o
worker, programa que executa a tarefa, confirmar o sucesso.

```text
1. A aplicação publica uma mensagem na exchange.

   aplicação -> exchange

2. A routing key escolhe a fila de destino.

   exchange
      |
      +-- order.created ----> fila principal
      |
      +-- order.cancelled --> fila alternativa

3. A fila principal possui seis mensagens.

   [evt-001] [evt-002] [evt-003] [evt-004] [evt-005] [evt-006]

4. Com prefetch=1, o worker recebe somente a primeira.

   worker <--- evt-001
   fila   [evt-002] [evt-003] [evt-004] [evt-005] [evt-006]

5. Sem confirmação, a próxima entrega espera.

   evt-001 sem ack
          |
          +--> evt-002 ainda não é entregue

6. O worker responde com nack e pede uma nova tentativa.

   worker -- nack + requeue --> fila

7. O RabbitMQ entrega evt-001 novamente.

   worker <--- evt-001, redelivered=true

8. O worker responde com ack. A mensagem termina e a próxima pode sair.

   worker -- ack --> evt-001 concluído
                     evt-002 pode ser entregue
```

Uma exchange recebe a mensagem e decide para qual fila enviá-la. A routing key é o
rótulo usado nessa decisão. `ack` confirma sucesso. `nack` informa que a entrega não
terminou, e `requeue` devolve a mensagem à fila para outra tentativa.

## A diferença principal

Kafka guarda eventos por um período configurado. Cada grupo controla até onde leu esse
histórico. RabbitMQ mantém mensagens pendentes e espera uma confirmação para encerrar
cada entrega.

| Pergunta | Kafka | RabbitMQ |
| --- | --- | --- |
| Ler remove a mensagem? | não | o `ack` encerra e remove a mensagem da fila |
| Como repetir? | ler novamente a partir de outro offset | devolver ou não confirmar a entrega |
| Como dois consumidores leem de forma independente? | cada um usa seu consumer group | cada fluxo precisa da própria fila |
| O que controla o progresso? | a posição do grupo em cada partição | a confirmação de cada mensagem |

## Para que isso serve em produção

Um histórico de alterações que precisa ser reprocessado combina naturalmente com um
log. Uma fila de tarefas distribuídas entre workers combina naturalmente com confirmação
por mensagem.

Isso não significa que Kafka serve apenas para eventos ou RabbitMQ apenas para jobs. A
decisão depende de retenção, replay, fan-out, roteamento, ordem e operação. O experimento
torna esses critérios concretos antes da escolha da ferramenta.

## Estrutura do experimento

- `scenario.yaml` define eventos, endpoints, tópico, queue e prefetch.
- `kafka_demo.py` publica por chave, consome e relê com outro group.
- `rabbit_demo.py` separa duas routing keys, segura uma entrega com prefetch, executa
  `nack`, redelivery e `ack`.
- `comparison.py` apresenta as duas formas de progresso sem criar uma API genérica de
  broker.
- `evidence/result.txt` guarda a última execução completa.

## Como executar

```bash
uv sync --locked
docker compose up -d --wait
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
RUN_BROKER_TESTS=1 uv run pytest -m integration
uv run python scripts/run_experiment.py
docker compose down -v
```

O teste padrão não exige infraestrutura e marca a integração como ignorada. O comando
com `RUN_BROKER_TESTS=1` exige os dois brokers ativos. A interface do RabbitMQ fica
disponível em `http://localhost:15673`, com usuário `forge` e senha local
`forge-secret`.

## O que observar

A saída do Kafka mostra `key`, partição e offset. Eventos de `order-a` preservam as
sequências 1, 2 e 3 dentro da mesma partição. Um segundo group recebe novamente os seis
registros. A ordem global dos seis pode mudar porque o Kafka não ordena eventos entre
partições diferentes. O group original, por outro lado, retoma depois dos offsets que
confirmou.

A saída do RabbitMQ mostra delivery tag, redelivery e decisão. Uma entrega recebe
`nack-requeue`. A mesma mensagem aparece novamente e só termina depois do `ack`. A
saída também mostra a sonda na queue alternativa e quantas entregas começaram enquanto
a primeira continuava sem confirmação.

## Resultado observado

**Medido:** o novo consumer group releu os seis registros. A ordem publicada foi
preservada dentro de cada chave, e o group que confirmou os offsets retomou no fim. No
RabbitMQ, cada routing key chegou à queue esperada. Com `prefetch=1`, somente a primeira
entrega começou antes da confirmação. O evento rejeitado voltou com `redelivered=true`
e terminou com `ack`.

## Limite do projeto

O laboratório usa um único nó de cada broker. Ele não prova replicação, disponibilidade,
throughput, exatamente uma vez, durabilidade diante de perda de disco ou escolha
universal. O Redpanda é usado pela compatibilidade com o protocolo Kafka, não como
comparação de produtos. A observação de prefetch usa um único consumer e não mede
backpressure sob carga.

## Resumo da ópera

Kafka registra eventos e cada grupo controla sua posição. RabbitMQ entrega trabalho e
espera confirmação. Escolher entre eles começa pelo modelo de entrega, não pelo nome da
tecnologia.
