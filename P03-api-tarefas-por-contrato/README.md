# P03: API de tarefas por contrato

Uma API não é apenas um conjunto de URLs. Ela precisa deixar claro quais dados
aceita, quais respostas devolve e como representa cada erro. Este laboratório usa
FastAPI e Pydantic para transformar essas regras em um contrato visível e testável.

## O que a API faz

| Método | Rota | Resultado |
| --- | --- | --- |
| `POST` | `/tasks` | cria uma tarefa pendente |
| `GET` | `/tasks/{id}` | devolve uma tarefa existente |
| `PATCH` | `/tasks/{id}/complete` | conclui uma tarefa pendente |

Uma tarefa só pode ser concluída uma vez. A segunda tentativa devolve `409 Conflict`
e não altera os dados.

## Preparação e execução

```bash
make setup
make check
make demo
```

Para iniciar o servidor:

```bash
make run
```

Depois, abra `http://127.0.0.1:8000/docs`. O FastAPI monta essa página a partir do
contrato OpenAPI da própria aplicação.

Todas as rotas exigem o cabeçalho `X-User-ID`. O cabeçalho `X-Request-ID` é opcional.
Se ele não for enviado, a API cria um identificador para a requisição.

## Exemplo

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H 'content-type: application/json' \
  -H 'X-User-ID: matheus' \
  -H 'X-Request-ID: demo-1' \
  -d '{"title":"Entender Depends","description":"Concluir o P03"}'
```

O retorno usa um modelo diferente do modelo de entrada. A API acrescenta ID, estado,
autor e datas sem aceitar esses campos no `POST`.

## Onde entra a injeção de dependência

As rotas declaram que precisam de três informações:

- identidade, obtida de `X-User-ID`;
- contexto da requisição, com horário e identificador;
- repositório, responsável por salvar e buscar tarefas.

O `Depends` do FastAPI prepara esses valores e os entrega para a rota. A regra de
negócio recebe objetos Python comuns e não conhece `Request` ou `Response`.

Na execução normal, o repositório guarda as tarefas em um dicionário na memória. Em
um teste, ele pode ser substituído por um fake com `app.dependency_overrides`. Isso
permite provocar uma falha controlada sem modificar o código interno da aplicação.

## Erros observáveis

```text
payload inválido       -> 422 Unprocessable Entity
tarefa ausente         -> 404 Not Found
conclusão repetida     -> 409 Conflict
repositório indisponível -> 503 Service Unavailable
identidade ausente     -> 401 Unauthorized
```

Execute todos esses casos com:

```bash
make experiment
```

O contrato salvo pode ser atualizado com `make openapi` e consultado em
`evidence/openapi.json`.

## Por que os dados ficam em memória

O objetivo deste projeto é entender contratos HTTP e injeção de dependência. Um banco
adicionaria conceitos que não ajudam a responder essa pergunta. Por isso, o repositório
usa um dicionário. As tarefas existem enquanto a aplicação está ligada e desaparecem
quando o servidor reinicia.

## Limite do laboratório

O cabeçalho de identidade é apenas um valor de demonstração, não autenticação real.
A API também não possui listagem, exclusão, persistência ou controle de acesso
entre usuários.

## Resumo da ópera

Pydantic define os dados aceitos e devolvidos. FastAPI transforma esses modelos em
validação e OpenAPI. `Depends` fornece identidade, contexto e repositório. O service
protege a regra de negócio sem depender do framework. O repositório em memória mantém
o foco nesses conceitos e pode ser trocado nos testes.
