# P06: quando parar de chamar um provedor?

Um provedor fora do ar pode receber milhares de chamadas que não têm chance de dar
certo. Mesmo quando ele está saudável, uma rajada criada pela própria aplicação pode
sobrecarregá-lo.

Este projeto coloca dois portões antes do provider fake. O primeiro interrompe chamadas
durante uma falha contínua. O segundo limita quantas chamadas podem sair de uma vez.

## Pergunta principal

> Como parar chamadas inúteis durante uma falha e conter uma rajada sem usar espera real?

O fluxo é pequeno:

```text
chamada
   |
circuit breaker
   |
token bucket
   |
provider fake
```

O circuit breaker fica primeiro. Enquanto o circuito está aberto, a chamada para antes
de consumir um token.

## O que é um circuit breaker?

Circuit breaker significa disjuntor de circuito. Ele observa falhas seguidas e muda
entre três estados:

```text
closed -- 3 falhas --> open -- 5 segundos --> half-open
   ^                                            |       |
   |________________ sucesso ___________________|       |
                        open <_____ falha ______________|
```

- `closed`: as chamadas seguem para o provedor;
- `open`: as chamadas são recusadas localmente;
- `half-open`: uma única chamada de teste verifica se o provedor se recuperou.

Uma falha no `half-open` abre o circuito novamente e reinicia o intervalo. Um sucesso
fecha o circuito e zera a contagem de falhas.

O projeto conta apenas `ProviderUnavailable`, que representa indisponibilidade do
provedor. Uma recusa pelo limite local ou uma credencial inválida não indica que o
provedor caiu e não altera a contagem.

## O que é um token bucket?

Token bucket significa balde de fichas. Imagine uma catraca que começa com três fichas.
Cada chamada gasta uma. Quando as fichas acabam, novas chamadas são recusadas. O relógio
devolve uma ficha por segundo, sem ultrapassar a capacidade inicial.

No cenário deste projeto, uma rajada de cinco chamadas produz:

```text
3 chamadas permitidas
2 chamadas recusadas
```

Depois de um segundo, uma nova chamada pode passar. Os testes avançam um relógio manual.
Eles não usam `sleep` e sempre reproduzem a mesma sequência.

## Como executar

```bash
make setup
make check
make experiment
```

`make check` executa Ruff, Pyright e pytest. `make experiment` mostra as transições do
circuito, executa a rajada e salva o mesmo resultado em `evidence/result.txt`.

## Falha controlada

O `scenario.yaml` define:

- limite de três falhas consecutivas;
- intervalo de recuperação de cinco segundos;
- bucket com três tokens e reposição de um token por segundo;
- quatro falhas seguidas de um sucesso;
- rajada de cinco chamadas.

O experimento executa esta sequência:

1. Três falhas abrem o circuito.
2. Uma chamada imediata é recusada sem alcançar o provedor.
3. Cinco segundos depois, a chamada de teste falha e reabre o circuito.
4. Após mais cinco segundos, outra chamada de teste funciona e fecha o circuito.
5. Um cliente novo envia cinco chamadas no mesmo instante.
6. O bucket permite três e recusa duas.
7. Um segundo depois, o bucket permite mais uma chamada.

O provider fake usa resultados definidos antes da execução. Nenhuma chamada acessa a
internet.

## Como o segredo entra

`ProviderConfig.from_env()` carrega a credencial de uma variável de ambiente. O campo
usa `repr=False`, por isso o valor não aparece quando a configuração é inspecionada.
Os logs registram endpoint, estado e resultado, mas nunca registram a credencial.

O experimento usa um segredo controlado e procura esse valor literalmente nos logs
capturados. A execução falha se ele aparecer. Isso prova apenas que os caminhos de log
deste projeto não expõem o valor. Não substitui um gerenciador de segredos.

## Checkpoints

### C0: preparação

`make setup` cria uma `.venv` independente e instala as ferramentas registradas no
`uv.lock`.

### C1: caminho feliz

Uma chamada consome um token, chega ao provider fake e mantém o circuito fechado.

### C2: quebra

Três falhas abrem o circuito. Uma chamada extra é recusada localmente. Em outro cliente,
uma rajada maior que o bucket produz duas recusas.

### C3: prova

O relógio avança sem espera real. Uma falha no `half-open` reabre o circuito e um sucesso
posterior o fecha. Os testes verificam as transições, a reposição de tokens e a ausência
do segredo nos logs.

## Resultado observado

O cenário determinístico comprova estas condições:

| Condição | Resultado esperado |
| --- | --- |
| Terceira falha consecutiva | circuito `open` |
| Chamada enquanto `open` | recusada sem chegar ao provedor |
| Falha no `half-open` | circuito aberto por mais cinco segundos |
| Sucesso no `half-open` | circuito `closed` e contador zerado |
| Cinco chamadas com três tokens | três permitidas e duas recusadas |
| Um segundo de reposição | uma nova chamada permitida |
| Busca do segredo nos logs | nenhuma ocorrência |

Os valores medidos pela execução ficam em `LEARNING.md` e `evidence/result.txt`.

## Limite do que foi comprovado

O circuito e o bucket vivem na memória de um único processo. Duas instâncias teriam
contagens separadas. O cenário também usa concorrência igual a um e não prova segurança
entre threads.

O provider é um fake. O projeto não implementa retry, limite distribuído, chamada HTTP
real ou gestão de segredos. Essas escolhas ficam fora do escopo para manter visível a
regra de cada portão.

## Resumo da ópera

O circuit breaker evita insistir quando o provedor já demonstrou que está indisponível.
O token bucket impede que a própria aplicação envie uma rajada maior que o limite local.
Os dois mecanismos resolvem problemas diferentes e precisam classificar recusas e
falhas corretamente. Uma recusa local nunca deve fingir que o provedor caiu.
