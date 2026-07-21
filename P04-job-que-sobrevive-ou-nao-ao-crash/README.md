# P04: o job termina se a API cair?

Uma API pode aceitar uma tarefa e cair antes de terminar o trabalho. Nesse caso, o
cliente recebe uma resposta de sucesso, mas o resultado nunca aparece.

Este projeto reproduz essa falha. Ele também mostra como uma chamada lenta pode travar
outras requisições quando usamos `async def` no lugar errado.

## O que este projeto responde

A pergunta principal é:

> Uma tarefa iniciada com `BackgroundTasks` sobrevive se o processo da API parar?

Não. A tarefa roda dentro do mesmo processo, que é o programa da API em execução. Se
esse processo morrer, a tarefa morre junto.

O projeto também responde outras perguntas:

- Quando devo criar uma rota com `def`?
- Quando devo usar `async def`?
- Como a API abre e fecha recursos com segurança?
- Como identificar uma requisição nos logs?

## Como executar

Prepare o ambiente e verifique o projeto:

```bash
make setup
make check
```

Depois, execute o experimento completo:

```bash
make experiment
```

Para iniciar a API e testar as rotas manualmente:

```bash
make run
```

A documentação interativa ficará disponível em `http://127.0.0.1:8000/docs`.

## Rotas disponíveis

| Método | Rota | O que ela mostra |
| --- | --- | --- |
| `GET` | `/health` | confirma que a API e seus recursos estão ativos |
| `GET` | `/work/sync` | executa uma chamada lenta sem travar o fluxo assíncrono |
| `GET` | `/work/async-blocking` | mostra o uso incorreto de uma chamada lenta em `async def` |
| `POST` | `/jobs` | inicia uma tarefa com `BackgroundTasks` |

## Por que uma rota trava e a outra não?

O projeto simula uma biblioteca síncrona com `time.sleep`. Uma biblioteca síncrona
mantém a thread ocupada até terminar a operação.

Na rota `/work/sync`, usamos `def`:

```python
def sync_work(...):
    blocking_library_call(...)
```

O FastAPI envia essa função para um thread pool, que é um grupo de threads usado para
executar chamadas síncronas. Assim, o event loop continua livre. O event loop é o
coordenador das operações assíncronas da aplicação.

Na rota `/work/async-blocking`, usamos `async def`, mas chamamos a mesma função
síncrona:

```python
async def async_blocking_work(...):
    blocking_library_call(...)
```

Essa chamada ocupa o event loop. Enquanto ela não termina, outras operações
assíncronas precisam esperar.

No experimento local, quatro requisições com atraso de 0,15 segundo produziram estes
resultados:

| Rota | Tempo total |
| --- | ---: |
| `/work/sync` | 0,161 s |
| `/work/async-blocking` | 0,620 s |

A rota com o bloqueio incorreto levou 3,85 vezes mais tempo.

## O que acontece com a tarefa em segundo plano?

O endpoint `/jobs` usa `BackgroundTasks`. Esse recurso permite responder ao cliente e
continuar um trabalho dentro do processo da API.

Durante uma execução normal, o projeto registra dois eventos:

```text
job_started
job_completed
```

O experimento inicia outra tarefa e encerra o processo antes do fim. Nesse caso, o
registro contém apenas:

```text
job_started
```

O evento `job_completed` nunca é gravado. Isso prova que `BackgroundTasks` não oferece
garantia de conclusão após uma queda.

A resposta `202 Accepted` também não significa que o trabalho terminou. Ela informa
somente que a API aceitou a tarefa.

## Quando usar `BackgroundTasks`?

Use `BackgroundTasks` quando perder o trabalho não causar um problema sério. Alguns
exemplos são uma limpeza temporária ou uma atualização que pode ser refeita.

Se a tarefa precisa terminar mesmo após uma queda, use uma fila durável. Uma fila
durável salva a tarefa fora do processo da API para que outro programa possa executá-la
ou tentar novamente.

Exemplos de trabalhos que pedem uma fila durável:

- processar um pagamento;
- enviar uma comunicação obrigatória;
- gerar um documento solicitado pelo usuário;
- atualizar dados que não podem ser perdidos.

Este projeto não implementa a fila. O objetivo é mostrar por que ela seria necessária.

## Como a API abre e fecha recursos?

O FastAPI chama de lifespan o ciclo de vida da aplicação. Esse ciclo possui dois
momentos:

- startup, quando a API está iniciando;
- shutdown, quando a API está encerrando.

No startup, o projeto abre um cliente e um recurso simulados. No shutdown, ele fecha os
dois. Os testes comprovam que cada componente fecha uma única vez.

O experimento também provoca falhas durante a abertura e o fechamento. Mesmo assim, o
projeto limpa os componentes que já estavam abertos.

## Para que serve o `correlation_id`?

O `correlation_id` é um código que identifica uma requisição. Ele ajuda a localizar nos
logs todos os eventos relacionados à mesma chamada.

Você pode enviar o código no cabeçalho:

```text
X-Correlation-ID: meu-teste-123
```

A API devolve o mesmo código na resposta. Se o cabeçalho não existir, ela cria um UUID,
que é um identificador único.

## Evidências

O resumo do experimento está em `evidence/result.txt`. Os arquivos com extensão
`.jsonl` guardam um evento JSON por linha. Eles mostram quais eventos foram gravados
antes do encerramento de cada processo.

## Limite do que foi comprovado

O projeto usa atrasos e recursos simulados. Ele não mede a capacidade de uma aplicação
em produção. Ele também não implementa fila, repetição automática ou recuperação de
tarefas.

O experimento comprova apenas estes pontos:

- uma chamada síncrona dentro de `async def` pode bloquear outras requisições;
- os recursos fecham durante um `graceful shutdown`;
- uma `BackgroundTask` pode desaparecer quando o processo da API morre.

## Resumo da ópera

Use `async def` com bibliotecas realmente assíncronas. Use `def` para chamadas
síncronas que podem rodar no thread pool. Use `BackgroundTasks` somente quando perder a
tarefa for aceitável. Se o trabalho precisa sobreviver a uma queda, salve-o fora do
processo da API em uma fila durável.
