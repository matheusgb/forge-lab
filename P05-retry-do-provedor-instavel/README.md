# P05: quando vale a pena tentar novamente?

Um provedor externo pode falhar por alguns segundos e voltar ao normal. Repetir a
chamada pode resolver o problema. Também pode duplicar uma cobrança, um pedido ou outro
efeito que já aconteceu.

Este projeto cria um cliente HTTP que só repete operações consideradas seguras.

## Pergunta principal

> Como repetir uma chamada após uma falha temporária sem repetir uma operação perigosa?

O cliente observa duas informações:

- o tipo da falha;
- se a operação pode ser executada novamente sem criar outro efeito.

Uma operação com essa segunda propriedade é chamada de idempotente. Ler o mesmo recurso
duas vezes costuma ser seguro. Criar o mesmo pagamento duas vezes não é.

## Como executar

```bash
make setup
make check
make experiment
```

O experimento imprime cada tentativa, as esperas calculadas e a decisão final. O mesmo
resultado fica salvo em `evidence/result.txt`.

## O que o provider fake faz

O provider fake usa o transporte de teste do `httpx2`. Ele não acessa a internet. Cada
cenário define antecipadamente o que acontecerá em cada chamada:

```text
500, 500, 200
429, 200
timeout, 200
400
500 em uma operação não idempotente
```

Isso permite repetir exatamente a mesma falha em todos os testes.

## Quais falhas são repetidas?

| Resultado | Decisão para uma leitura segura |
| --- | --- |
| `2xx` | devolver a resposta |
| `400` | parar imediatamente |
| `429` | esperar e tentar novamente |
| `5xx` | esperar e tentar novamente |
| timeout | esperar e tentar novamente |

O status `400` indica um problema na requisição. Repetir os mesmos dados não deve
corrigi-lo. Os status `5xx` indicam uma falha no servidor e podem ser temporários. O
status `429` informa que o cliente enviou chamadas demais.

A matriz completa, incluindo a operação não idempotente, está em
`evidence/decision-matrix.md`.

## Backoff, jitter e `Retry-After`

O cliente não repete a chamada imediatamente. Ele usa backoff exponencial, que aumenta
a espera depois de cada falha:

```text
0,5 s, 1,0 s, 2,0 s...
```

O jitter acrescenta uma pequena variação aleatória. Essa variação reduz a chance de
muitos clientes repetirem a chamada no mesmo instante.

Quando o provedor devolve `Retry-After`, o cliente respeita o tempo indicado. O
cabeçalho pode conter uma quantidade de segundos ou uma data HTTP.

Nos testes, relógio, espera e valor aleatório são objetos injetados. Nenhum teste usa
`sleep` real. O código apenas registra quanto tempo teria esperado.

## Timeouts

O cliente configura limites separados para conexão e leitura:

- connect timeout: tempo máximo para abrir a conexão;
- read timeout: tempo máximo para receber dados depois da conexão.

Um timeout não informa se o provedor concluiu a operação antes de a resposta se perder.
Por isso, o projeto não repete uma criação não idempotente após timeout ou `5xx`.

## Resultado observado

Com três tentativas e um valor aleatório fixo, o experimento produziu:

| Cenário | Tentativas | Esperas | Decisão final |
| --- | ---: | --- | --- |
| `500, 500, 200` | 3 | 0,55 s e 1,10 s | sucesso |
| `429, 200` | 2 | 2,00 s | sucesso |
| `timeout, 200` | 2 | 0,55 s | sucesso |
| `400` | 1 | nenhuma | erro definitivo |
| `POST` com `500` | 1 | nenhuma | operação insegura |

## Limite do que foi comprovado

O provider é um fake em memória. O projeto não mede a disponibilidade de um serviço
real e não implementa circuit breaker, rate limit ou chave de idempotência.

O experimento comprova apenas a política local: falhas temporárias são repetidas dentro
do limite quando a operação é segura. Uma criação insegura para na primeira falha.

## Resumo da ópera

Retry não significa repetir qualquer erro. O cliente deve reconhecer falhas temporárias,
limitar as tentativas, aumentar a espera e considerar o efeito da operação. Quando não
há garantia de idempotência, parar pode ser mais seguro do que tentar novamente.
