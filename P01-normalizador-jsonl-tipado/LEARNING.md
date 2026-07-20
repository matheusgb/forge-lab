# Learning log

## Premissa

Seis linhas sintéticas representam entradas independentes. O JSONL permite
classificar uma linha sem precisar descartar o restante do arquivo.

## Meta

Obter duas saídas cuja soma de linhas seja igual à entrada, preservar a causa dos
erros conhecidos e interromper quando a própria escrita deixa de ser confiável.

## Medido

- Python: 3.14.6; uv: 0.11.29.
- `make check`: Ruff passou, Pyright retornou 0 erros e os 8 testes passaram.
- cenário misto: 6 entradas produziram 2 válidas e 4 rejeitadas; a invariante
  `total == valid + rejected` foi verdadeira.
- escrita quebrada: `OutputWriteError` foi emitido na linha esperada e preservou
  um `OSError` em `__cause__`.

## Trade-off

O `Result[T]` deixa falhas esperadas explícitas sem usar exceções como fluxo no
processador. Dentro dos parsers, exceções de domínio ainda são úteis para adicionar
contexto e manter a causa da biblioteca padrão com `raise ... from error`.

## Próximo limite

As duas saídas não são uma transação atômica. Resolver queda entre duas escritas
exigiria outro desenho, como staging seguido de rename ou armazenamento transacional.
