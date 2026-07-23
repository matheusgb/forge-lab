# P01: Normalizador JSONL tipado

Este projeto recebe pedidos com dados imperfeitos e garante que cada linha termine
classificada como válida ou rejeitada.

## Como o programa funciona

O programa lê um arquivo JSONL, formato no qual cada linha contém um JSON independente.
Ele valida e normaliza um pedido por vez. Pedidos válidos vão para `valid.jsonl`.
Pedidos inválidos vão para `rejected.jsonl` com o número da linha e o motivo.

```text
orders-mixed.jsonl
        |
        v
validar e normalizar
   |             |
   v             v
valid.jsonl   rejected.jsonl
```

Ao final, o programa verifica esta regra:

```text
total de linhas = válidas + rejeitadas
```

Moeda, data, valor, tags e espaços são normalizados. Uma falha nos dados rejeita apenas
a linha atual. Uma falha de escrita encerra o programa, pois continuar poderia causar
perda silenciosa.

## Conceito abordado

O projeto aborda modelagem tipada e tratamento explícito de erros. O Pydantic converte
o JSON em um `Order` e concentra as regras dos campos no próprio modelo. O fluxo não
precisa repetir verificações de tipo para cada valor recebido.

Quando o Pydantic rejeita uma linha, o normalizador traduz o diagnóstico para uma única
exceção de domínio com código, campo e número da linha. O laço captura essa exceção,
grava a rejeição e continua. Uma falha de escrita usa outra exceção e encerra o lote.
Um `set` detecta IDs repetidos e um `Counter` acumula os motivos das rejeições.

## Para que isso serve em produção

Integrações recebem planilhas, eventos e arquivos de parceiros com dados incompletos.
O sistema precisa aproveitar registros corretos sem esconder os incorretos.

Exemplo: um marketplace importa mil pedidos. Dois contêm uma moeda desconhecida. O
normalizador envia 998 pedidos válidos ao próximo estágio e separa os outros dois com
um motivo claro para correção. A soma das saídas prova que nenhum pedido desapareceu.

## Como executar

```bash
uv sync --locked
uv run ruff check .
uv run pyright
uv run pytest
```

Para executar o cenário misto:

```bash
uv run normalize-orders \
  fixtures/orders-mixed.jsonl \
  output/valid.jsonl \
  output/rejected.jsonl
uv run pytest tests/test_processor.py::test_output_error_preserves_os_error_as_cause -q
```

## Resultado observado

O cenário misto processou seis linhas: duas válidas e quatro rejeitadas. Os oito testes,
o Ruff e o Pyright passaram. O Pydantic ficou restrito à validação do contrato. O teste
de escrita gerou `OutputWriteError` e preservou o `OSError` original como causa.

```json
{"total":6,"valid":2,"rejected":4,"invariant":true}
```

O resultado completo está em `evidence/result.txt`.

## Limite do projeto

Os dois arquivos de saída não formam uma transação única. Uma interrupção entre as
gravações pode deixá-los incompletos. Um sistema real poderia gravar arquivos
temporários e renomeá-los ao final, ou usar um armazenamento transacional.

## Resumo da ópera

Dados ruins não precisam derrubar o lote inteiro, mas também não podem sumir. Tipos,
erros de domínio e uma regra de contagem tornam cada decisão explícita e auditável.
