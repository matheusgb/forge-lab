# P01 — Normalizador JSONL tipado

Uma CLI pequena que lê um pedido por linha, normaliza os válidos e explica por que
cada linha inválida foi rejeitada. Uma entrada ruim não interrompe as próximas
quando continuar é seguro.

## Pergunta

Como modelar dados e erros em Python de modo que nenhuma linha desapareça e a
causa original continue disponível para diagnóstico?

## Setup e execução

```bash
make setup
make check
make demo
```

O comando equivalente à demo é:

```bash
uv run normalize-orders \
  fixtures/orders-mixed.jsonl \
  output/valid.jsonl \
  output/rejected.jsonl
```

A saída-resumo esperada é:

```json
{"total":6,"valid":2,"rejected":4,"invariant":true}
```

Veja os dois arquivos com `make experiment`. O cenário fixo contém moeda
desconhecida, data impossível, campo ausente e JSON quebrado; o mesmo comando roda
o teste que simula falha durante a escrita.

## Checkpoints

- **C0 — starter:** `make setup && make check` prepara o projeto.
- **C1 — caminho feliz:** uma linha válida vira um `Order` normalizado.
- **C2 — quebra:** quatro linhas ruins são classificadas sem esconder as seguintes.
- **C3 — prova:** testes cobrem as classes de erro, escrita quebrada e a invariante.

## Onde estão os conceitos

- `dataclass`: `Order`, `Money`, `Result` e `Summary`.
- `Enum`: moedas aceitas e códigos de erro.
- composição: `Order` contém `Money`.
- `Optional`: `note` é representado por `str | None`.
- genérico: `Result[T]` carrega um valor tipado ou erro.
- `list` e `tuple`: tags são montadas numa lista e congeladas numa tupla.
- `set`: remove tags repetidas e detecta IDs duplicados.
- `dict`: representa JSON e contabiliza erros por código.
- context manager: abre e sempre fecha as duas saídas.
- exceção encadeada: `raise ... from error` mantém `__cause__`.

## Regra de continuação

Erros pertencentes a uma linha são escritos em `rejected.jsonl`, e o processamento
continua. Falha na própria saída é diferente: continuar perderia registros, então a
CLI interrompe com `OutputWriteError` e mantém o `OSError` original como causa.

## Demo de três minutos

1. Rode `make demo` e confira que `6 = 2 + 4`.
2. Mostre uma linha normalizada e uma rejeitada.
3. Aponte `Result[T]`, `Order` composto com `Money` e uma exceção com `from`.
4. Rode o teste `test_output_error_preserves_os_error_as_cause`.

## Não foi provado

Não há API, dataframe, banco, paralelismo ou garantia transacional entre os dois
arquivos de saída. O teste comprova comportamento local com o fixture versionado.
