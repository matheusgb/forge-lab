# P01: Normalizador JSONL tipado

Arquivos recebidos de outros sistemas nem sempre chegam perfeitos. Um pedido pode
ter uma moeda desconhecida, uma data inválida ou até um JSON incompleto. O programa
não deve esconder essas linhas nem descartar todo o arquivo por causa de um erro.

Este laboratório cria um programa de linha de comando que classifica cada pedido
como válido ou rejeitado e registra o motivo da decisão.

## Como o programa funciona

O arquivo de entrada usa JSONL, um formato no qual cada linha contém um JSON
independente. Isso permite continuar depois de uma linha inválida.

```text
linha do arquivo
      |
      v
validar e normalizar
      |
      +--> pedido válido  --> valid.jsonl
      |
      +--> pedido inválido --> rejected.jsonl
```

No final, esta regra precisa ser verdadeira:

```text
total de linhas = válidas + rejeitadas
```

## Preparação e execução

```bash
make setup
make check
make experiment
```

O experimento processa seis pedidos:

```text
6 linhas recebidas
2 pedidos válidos
4 pedidos rejeitados
```

A CLI também pode ser executada diretamente:

```bash
uv run normalize-orders \
  fixtures/orders-mixed.jsonl \
  output/valid.jsonl \
  output/rejected.jsonl
```

O resumo confirma que nenhuma linha desapareceu:

```json
{"total":6,"valid":2,"rejected":4,"invariant":true}
```

`invariant: true` significa que `6 = 2 + 4`.

## O que é normalizado

- A moeda passa para letras maiúsculas, como `brl` para `BRL`.
- A data passa para UTC, um fuso horário comum entre sistemas.
- O valor monetário passa a ter duas casas decimais.
- Tags repetidas são removidas.
- Espaços desnecessários são removidos dos textos.

Se uma linha tiver moeda desconhecida, data impossível, campo obrigatório ausente
ou JSON inválido, ela será gravada em `rejected.jsonl` com o número da linha e o
motivo da rejeição.

## Conceitos de Python usados

- `dataclass` representa pedidos, valores monetários e resumos.
- `Enum` limita as moedas e os códigos de erro aceitos.
- `Result[T]` representa um pedido válido ou um erro conhecido.
- `list`, `tuple`, `set` e `dict` organizam tags, IDs e contagens.
- O gerenciador de contexto garante que os arquivos sejam fechados.
- `raise ... from error` preserva o erro original para diagnóstico.

## Quando o programa deve parar

Um erro nos dados afeta apenas a linha atual. O programa registra a rejeição e segue
para a próxima linha. Uma falha ao gravar os arquivos é diferente. Nesse caso, o
programa para porque continuar poderia fazer pedidos desaparecerem sem registro.

## Limite do laboratório

Os dois arquivos de saída não são gravados como uma única operação indivisível. O
projeto também não possui API, banco de dados ou processamento paralelo.

## Resumo da ópera

Cada linha precisa terminar em um lugar conhecido. Pedidos válidos vão para
`valid.jsonl`. Pedidos inválidos vão para `rejected.jsonl` com uma explicação. Erros
nos dados não interrompem o arquivo inteiro, mas uma falha na gravação interrompe o
programa para evitar perda silenciosa.
