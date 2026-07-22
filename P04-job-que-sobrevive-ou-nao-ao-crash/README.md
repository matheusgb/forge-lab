# P04: O job termina se a API cair?

Este projeto mostra duas falhas comuns em APIs: bloquear o event loop com código
síncrono e perder uma tarefa em segundo plano quando o processo encerra.

## Como o programa funciona

A API oferece uma rota síncrona, uma rota assíncrona que bloqueia e um endpoint que
agenda jobs com `BackgroundTasks`. O lifespan abre e fecha recursos simulados. Um
middleware adiciona um `correlation_id` a cada requisição.

| Método | Rota | Comportamento observado |
| --- | --- | --- |
| `GET` | `/health` | confirma que os recursos estão ativos |
| `GET` | `/work/sync` | executa código síncrono no thread pool |
| `GET` | `/work/async-blocking` | bloqueia o event loop de forma intencional |
| `POST` | `/jobs` | agenda uma tarefa dentro do processo da API |

O experimento inicia um job, encerra o processo antes da conclusão e consulta os
eventos gravados. O registro contém `job_started`, mas não contém `job_completed`.

## Conceito abordado

O event loop coordena as operações assíncronas. Uma função bloqueante, como
`time.sleep`, impede que ele avance quando é chamada diretamente dentro de `async def`.
Uma rota `def` é executada pelo FastAPI em um thread pool e não ocupa o event loop.

`BackgroundTasks` executa o job depois da resposta, mas dentro do mesmo processo da
API. Se o processo morrer, o job também morre. O lifespan, por sua vez, controla a
abertura e o fechamento de recursos no startup e no shutdown.

## Para que isso serve em produção

Essas escolhas afetam a capacidade de resposta e a confiabilidade da aplicação.

Exemplo: redimensionar uma imagem descartável pode usar `BackgroundTasks` se o cliente
puder tentar novamente. Processar um pagamento não deve depender desse mecanismo. A
API precisa persistir a tarefa em uma fila durável antes de responder, para que outro
processo consiga retomá-la após uma queda.

Outro exemplo é um SDK síncrono usado por uma rota. Enquanto não houver uma versão
assíncrona, uma rota `def` ou uma execução explícita em thread evita bloquear todas as
outras operações do event loop.

## Como executar

```bash
make setup
make check
make experiment
```

Para iniciar a API manualmente:

```bash
make run
```

A documentação fica em `http://127.0.0.1:8000/docs`.

## Resultado observado

Quatro requisições com 0,15 segundo de espera levaram 0,161 segundo na rota `def` e
0,620 segundo na rota `async def` bloqueante. No crash controlado, o job iniciou e não
concluiu. Sete testes também comprovaram que os recursos são fechados uma vez e que a
limpeza continua mesmo diante de falhas no startup ou no shutdown.

Os eventos e o resumo estão em `evidence/`.

## Limite do projeto

Os atrasos e recursos são simulados. O projeto não implementa fila, retry, idempotência
ou recuperação. Um graceful shutdown reduz interrupções, mas ainda pode terminar à
força depois de um prazo.

## Resumo da ópera

Use `async def` com operações realmente assíncronas. Isole chamadas síncronas do event
loop. Use `BackgroundTasks` apenas quando perder o job for aceitável. Trabalho crítico
precisa ser persistido fora do processo da API.
