# P07: Contrato HTTP paginado

Este projeto mostra como consumir uma coleção paginada sem duplicar itens quando novos
registros entram no topo. Ele também verifica como o contrato pode evoluir sem quebrar
um consumidor antigo.

## Como o programa funciona

Um provider fake expõe comentários em ordem decrescente. O cliente recebe uma página,
valida os campos, guarda os itens e usa `next_cursor` para buscar a página seguinte.

```text
cliente                   provider
   |                         |
   | cursor atual            |
   |------------------------>|
   | itens + next_cursor     |
   |<------------------------|
   |                         |
```

O cursor é opaco para o cliente. Neste provider, ele representa duas posições:

- o maior ID existente quando a leitura começou;
- o último ID entregue na página anterior.

Essa combinação mantém uma janela estável. Um comentário criado depois do início não
entra no meio da leitura. Ele aparece quando o cliente inicia uma nova consulta.

Pydantic transforma cada resposta em `Page` e valida o contrato declarativo. O cliente
fica responsável apenas pelo percurso do cursor e pelas invariantes da paginação.

O cliente também interrompe cursor repetido, item duplicado, página vazia com continuação
e resposta que não respeita o schema esperado.

## Solução usada no projeto

O projeto substitui `OFFSET` por paginação por cursor. O cursor carrega dois valores:

```text
snapshot_id = maior ID quando a leitura começou
after_id = último ID entregue ao cliente
```

Na primeira requisição, a lista contém `(6, 5, 4, 3, 2, 1)`. O provider devolve
`(6, 5)` e cria um cursor com `snapshot_id=6` e `after_id=5`.

Se o comentário 7 entrar antes da próxima requisição, o provider aplica esta regra:

```text
id <= snapshot_id e id < after_id
```

Neste caso, a regra vira `id <= 6 e id < 5`. A segunda página começa em 4. O comentário
5 não se repete porque não é menor que `after_id`. O comentário 7 não entra na leitura
atual porque é maior que `snapshot_id`.

Uma nova leitura começa sem cursor, cria `snapshot_id=7` e passa a enxergar o comentário
novo. Portanto, a solução implementada é keyset pagination pelo último ID, combinada
com uma fronteira de snapshot.

## Conceitos abordados

Paginação divide uma coleção em respostas menores. Paginação por cursor usa a posição
do último item como continuação. Quando o cursor também carrega um limite do início da
leitura, ele funciona como uma fronteira de snapshot, também chamada de high-water mark.

Evolução compatível acrescenta informação sem invalidar consumidores existentes. A
versão 2 do provider adiciona `author_badge`, um campo opcional que o consumidor da
versão 1 pode ignorar. Renomear o campo obrigatório `body` para `text` é incompatível e
gera um erro legível. O modelo declara que campos extras são ignorados, portanto essa
compatibilidade não depende de um parser manual.

## Dois problemas parecidos

Uma lista atualizada durante a leitura mistura dois problemas reais.

O primeiro é visual. Inserir conteúdo acima do que a pessoa está lendo pode mover o
viewport, a área visível da página. Esse comportamento costuma ser chamado de content
jump ou layout shift. A técnica para manter o mesmo elemento na mesma posição é scroll
anchoring, também chamada de preservação da posição de rolagem.

O segundo problema está nos dados. Se a API usa `OFFSET`, uma inserção no topo desloca
as posições. A página seguinte pode repetir ou omitir itens. Esse efeito é conhecido
como pagination drift. Cursor estável ou keyset pagination evita depender da posição
numérica que mudou.

## Para que isso serve em produção

Em uma seção de comentários ao vivo, o sistema pode receber novidades por polling,
WebSocket ou Server-Sent Events. A solução normalmente combina duas decisões:

1. A API pagina comentários antigos com cursor e uma fronteira de snapshot.
2. O frontend guarda comentários novos em um buffer e mostra “3 novos comentários”.
3. Quando a pessoa decide exibi-los, o frontend mantém um item visível como âncora ou
   compensa a diferença de altura no `scrollTop`.

Alguns navegadores já aplicam scroll anchoring em situações simples por meio da
propriedade CSS `overflow-anchor`. Interfaces com listas virtuais ou atualizações
complexas ainda costumam preservar explicitamente o ID e a posição do item visível.

Se a tela não precisa ser atualizada ao vivo, buscar apenas no carregamento é uma
solução válida. Ela troca atualização imediata por estabilidade. Os mecanismos acima
se tornam necessários quando o produto precisa receber novidades durante a leitura.

## Exemplo reproduzido

A primeira página contém os comentários 6 e 5. Antes da segunda requisição, o comentário
7 entra no topo.

```text
antes:       6, 5, 4, 3, 2, 1
depois:   7, 6, 5, 4, 3, 2, 1
```

Com `OFFSET 2`, a segunda página começa novamente no comentário 5. Com o cursor ancorado
no comentário 5 e limitado ao snapshot 6, a segunda página retorna 4 e 3. O comentário
7 fica pendente para uma nova leitura.

## Como executar

```bash
uv sync --locked
uv run ruff check .
uv run pyright
uv run pytest
uv run python scripts/run_experiment.py
uv run python scripts/run_experiment.py --step-by-step
```

O primeiro comando do experimento executa a paginação normal, insere um comentário
entre páginas, compara offset e cursor e provoca duas quebras de contrato. O resultado
fica em `evidence/result.txt`.

O modo `--step-by-step` executa somente o percurso por cursor. Ele mostra a chamada
`provider.get_page(cursor=...)`, o JSON bruto recebido e o valor de `next_cursor` usado
na chamada seguinte. Quando o JSON traz `next_cursor: null`, a saída explica por que o
cliente encerra a leitura. Esse modo escreve apenas no terminal e não altera a evidência.

## Resultado observado

**Medido:** o baseline retornou `(6, 5, 4, 3, 2, 1)` em três páginas. Após a inserção,
o offset retornou o comentário 5 duas vezes. O cursor manteve os seis comentários
originais sem repetição. Uma nova leitura começou por `(7, 6)`.

O consumidor v1 aceitou o campo opcional da v2. Ele rejeitou o `body` ausente com o
caminho exato do erro. O cliente também interrompeu um cursor repetido antes de fazer
uma terceira chamada.

## Limite do projeto

O provider é local e usa IDs crescentes como ordem. O projeto não implementa HTTP real,
banco, assinatura do cursor, exclusão concorrente ou frontend. O cursor demonstra o
contrato e a estabilidade da janela. Índices e paginação de banco entram no P11.

## Resumo da ópera

Scroll anchoring mantém a leitura no mesmo lugar. Cursor com snapshot evita que
inserções mudem as páginas já iniciadas. Em feeds ao vivo, o frontend ainda pode
acumular novidades e deixar a pessoa decidir quando inseri-las no topo.
