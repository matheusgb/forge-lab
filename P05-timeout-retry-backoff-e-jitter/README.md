# P05: Quando vale a pena tentar novamente?

Este projeto cria um cliente HTTP que repete falhas temporárias somente quando a
operação pode ser executada de novo com segurança.

## Como o programa funciona

Um provider fake devolve sequências previsíveis de respostas, como `500, 500, 200`,
`429, 200`, timeout ou `400`. O cliente classifica a falha e a operação antes de decidir
se tenta novamente.

```text
chamada HTTP
     |
     v
classificar falha e operação
     |
     +--> segura e temporária --> esperar --> tentar novamente
     |
     +--> definitiva ou insegura --> parar
```

O cliente aumenta o intervalo entre tentativas, adiciona uma pequena variação e
respeita o cabeçalho `Retry-After`. Relógio, espera e aleatoriedade são injetados, então
os testes não usam `sleep` real.

Tenacity controla o ciclo e o limite de tentativas. O código do projeto mantém visível
o que pertence à regra da integração: quais erros são temporários, quais operações são
seguras e quanto tempo o cliente deve esperar.

## Conceito abordado

Retry é a repetição controlada de uma operação após uma falha. Backoff exponencial
aumenta o intervalo entre as tentativas. Jitter adiciona variação para evitar que muitos
clientes repitam ao mesmo tempo.

Idempotência significa que repetir uma operação produz o mesmo efeito lógico. Uma
leitura costuma ser idempotente. Criar um pagamento sem uma chave de idempotência pode
gerar duas cobranças.

## Para que isso serve em produção

Integrações externas apresentam timeouts, limites de uso e indisponibilidades curtas.
Um retry bem definido recupera parte dessas falhas sem aumentar uma sobrecarga ou
duplicar efeitos.

Exemplo: um serviço consulta o status de uma entrega e recebe `503`. Ele espera, tenta
novamente e obtém sucesso. Se o mesmo timeout ocorrer depois do envio de um pagamento,
o cliente para porque não sabe se o provedor processou a primeira chamada. Ele só
poderia repetir com uma garantia explícita, como uma chave de idempotência aceita pelo
provedor.

## Como executar

```bash
uv sync --locked
uv run ruff check .
uv run pyright
uv run pytest
uv run python scripts/run_experiment.py
```

O experimento imprime as tentativas e salva o resultado em `evidence/result.txt`. A
política completa está em `evidence/decision-matrix.md`.

## Política testada

| Resultado | Leitura idempotente | Criação não idempotente |
| --- | --- | --- |
| `2xx` | devolver resposta | devolver resposta |
| `400` | parar | parar |
| `429` | tentar novamente | parar |
| `5xx` | tentar novamente | parar |
| timeout | tentar novamente | parar |

## Resultado observado

Dezessete testes, Ruff e Pyright passaram. O cenário `500, 500, 200` concluiu em três
tentativas com esperas simuladas de 0,55 e 1,10 segundo. O `429` respeitou dois segundos
de `Retry-After`. O `400` e o `500` em uma criação insegura pararam na primeira
tentativa. Nenhuma espera real ocorreu.

## Limite do projeto

O provider existe apenas em memória. O projeto não testa rede real, circuit breaker ou
rate limit. Ele também não envia chave de idempotência, pois essa garantia depende do
contrato de cada provedor.

## Resumo da ópera

Retry exige classificação. Repita apenas falhas temporárias, limite as tentativas e
considere o efeito da operação. Quando a idempotência não está garantida, parar pode ser
mais seguro do que tentar novamente.
