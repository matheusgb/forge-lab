# P03: API de tarefas por contrato

Este projeto cria uma API pequena na qual entradas, saídas e erros possuem formatos
explícitos.

## Como o programa funciona

A API recebe uma requisição, valida os dados com Pydantic, executa a regra no service e
usa um repositório em memória para guardar as tarefas.

```text
requisição HTTP
      |
      v
FastAPI e Pydantic
      |
      v
service de tarefas
      |
      v
repositório em memória
```

| Método | Rota | Resultado |
| --- | --- | --- |
| `POST` | `/tasks` | cria uma tarefa pendente |
| `GET` | `/tasks/{id}` | devolve uma tarefa existente |
| `PATCH` | `/tasks/{id}/complete` | conclui uma tarefa pendente |

Uma tarefa só pode ser concluída uma vez. A segunda tentativa retorna `409 Conflict` e
não altera o estado.

## Conceito abordado

O projeto aborda contrato HTTP e injeção de dependência. O contrato define os campos
aceitos, as respostas e os erros. O FastAPI publica esse contrato em OpenAPI.

Injeção de dependência significa entregar ao código os recursos de que ele precisa. O
`Depends` fornece identidade, contexto da requisição e repositório. A regra de negócio
recebe objetos Python comuns e não depende de `Request` ou `Response`.

## Para que isso serve em produção

Contratos claros permitem que frontend, aplicativos e outros serviços integrem com a
API sem adivinhar formatos. A separação das dependências permite trocar infraestrutura
e testar falhas sem alterar a regra de negócio.

Exemplo: a aplicação usa PostgreSQL em produção. Durante um teste, o repositório é
trocado por um fake que simula indisponibilidade. O teste confirma a resposta `503`
sem precisar derrubar um banco real e sem modificar o service.

## Como executar

```bash
uv sync --locked
uv run ruff check .
uv run pyright
uv run pytest
uv run python scripts/demo.py
```

Para iniciar a API:

```bash
uv run uvicorn task_api.main:app --reload
```

A documentação interativa fica em `http://127.0.0.1:8000/docs`. Todas as rotas exigem
`X-User-ID`. O cabeçalho `X-Request-ID` é opcional.

Exemplo de criação:

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H 'content-type: application/json' \
  -H 'X-User-ID: matheus' \
  -d '{"title":"Entender Depends","description":"Concluir o P03"}'
```

## Falhas observáveis

```text
payload inválido          -> 422 Unprocessable Entity
tarefa ausente            -> 404 Not Found
conclusão repetida        -> 409 Conflict
repositório indisponível  -> 503 Service Unavailable
identidade ausente        -> 401 Unauthorized
```

`uv run pytest tests/test_api.py -v` executa esses casos. O comando
`uv run python scripts/export_openapi.py` atualiza o contrato salvo em
`evidence/openapi.json`.

## Resultado observado

Ruff e Pyright passaram sem erros. Oito testes validaram regra, contrato e falhas. O
OpenAPI salvo contém as três rotas, seus schemas e suas respostas.

## Limite do projeto

As tarefas desaparecem quando a aplicação reinicia. `X-User-ID` é apenas um valor de
demonstração e não oferece autenticação ou autorização. O projeto não possui listagem,
exclusão ou banco de dados.

## Resumo da ópera

Pydantic define os dados. FastAPI transforma os modelos em validação e OpenAPI.
`Depends` separa os recursos da regra de negócio. Essa estrutura deixa o contrato
visível e permite trocar dependências nos testes.
