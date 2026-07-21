# Registro de aprendizado

## Premissa

Um repositório em memória atende ao contrato durante a execução normal. Um fake
substitui esse repositório nos testes. Nenhum dos dois muda a regra de conclusão.

## Meta

Validar entrada e saída pelo contrato, separar a regra de negócio do HTTP e trocar o
repositório usando o mecanismo público de dependências do FastAPI.

## Medido

- ambiente: Python 3.14.6, FastAPI 0.139.2, Pydantic 2.13.4 e httpx2 2.7.0.
- Ruff e Pyright: nenhum erro encontrado.
- testes: 8 testes passaram em 0,16 s.
- OpenAPI: contrato salvo em `evidence/openapi.json` com as três rotas, schemas e
  respostas de erro.
- falhas controladas: payload inválido retornou 422, tarefa ausente retornou 404,
  conclusão repetida retornou 409 e repositório indisponível retornou 503.

## Escolha e consequência

O repositório em memória mantém o projeto pequeno e deixa a troca de dependência
visível. Em contrapartida, as tarefas desaparecem quando a aplicação reinicia.

## Próximo limite

A identidade vem diretamente de um cabeçalho e não pode ser considerada autenticação.
Uma aplicação real precisaria validar credenciais e aplicar autorização.
