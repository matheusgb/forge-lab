# Registro de aprendizado

## Premissa

Um `MockTransport` representa o provedor externo. Os resultados são definidos antes da
execução, e a espera é apenas registrada. Nenhum cenário acessa a rede ou usa `sleep`
real.

## Meta

Repetir timeout, `429` e `5xx` somente em operações seguras. Respeitar `Retry-After`,
aplicar backoff exponencial com jitter e parar imediatamente diante de `400` ou de uma
falha em operação não idempotente.

## Medido

- ambiente: Python 3.14.6 e httpx2 2.7.0;
- Ruff e Pyright: nenhum erro encontrado;
- testes: 17 testes passaram em 0,03 s;
- dois status `500` foram seguidos por `200` em três tentativas, com esperas simuladas
  de 0,55 s e 1,10 s;
- `429` com `Retry-After: 2` esperou 2,00 s antes da segunda tentativa;
- timeout em leitura segura foi seguido por sucesso na segunda tentativa;
- `400` encerrou a chamada na primeira tentativa;
- `500` em criação não idempotente encerrou a chamada na primeira tentativa;
- timeouts configurados: 0,20 s para conexão e 0,50 s para leitura;
- nenhuma espera real ocorreu durante testes ou experimento.

## Escolha e consequência

A operação declara se aceita retry. Essa decisão evita inferir segurança apenas pelo
método HTTP. Em contrapartida, cada nova operação precisa receber uma classificação
explícita.

Relógio, espera e aleatoriedade são injetados. Os testes conseguem verificar os tempos
calculados sem depender do relógio real e sem tornar a suíte lenta.

## Próximo limite

O laboratório não envia chave de idempotência. Uma integração real poderia usar uma
chave aceita pelo provedor para repetir certas criações com segurança. Essa garantia
depende do contrato externo e não foi simulada aqui.
