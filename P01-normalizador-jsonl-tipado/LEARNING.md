# Registro de aprendizado

## Premissa

Seis linhas sintéticas representam entradas independentes. O JSONL permite
classificar uma linha sem precisar descartar o restante do arquivo.

## Meta

Obter duas saídas cuja soma de linhas seja igual à entrada, preservar a causa dos
erros conhecidos e interromper quando a própria escrita deixa de ser confiável.

## Medido

- Python: 3.14.6; uv: 0.11.29.
- `make check`: Ruff passou, Pyright retornou 0 erros e os 8 testes passaram.
- cenário misto: 6 entradas produziram 2 válidas e 4 rejeitadas. A regra
  `total == valid + rejected` foi respeitada.
- falha de escrita: `OutputWriteError` foi emitido na linha esperada e preservou
  um `OSError` em `__cause__`.

## Escolha e consequência

O `Result[T]` mostra de forma explícita se uma linha produziu um pedido ou um erro.
As funções que interpretam cada campo usam exceções de domínio para acrescentar o
número da linha e preservar o erro original com `raise ... from error`.

## Próximo limite

As duas saídas não são gravadas como uma única operação indivisível. Se o programa
parar entre uma gravação e outra, os arquivos podem ficar incompletos. Evitar isso
exigiria arquivos temporários seguidos de renomeação ou um armazenamento transacional.
