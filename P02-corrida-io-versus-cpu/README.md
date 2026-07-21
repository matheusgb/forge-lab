# P02: Corrida I/O versus CPU

Concorrência não acelera todo tipo de código da mesma forma. Esperar uma resposta da
rede é diferente de executar um cálculo pesado. Por isso, este laboratório contém
dois experimentos separados: um para operações de I/O e outro para cálculos que usam
a CPU.

O objetivo não é colocar I/O contra CPU para descobrir qual dos dois é mais rápido.
Essa comparação não faria sentido porque são problemas diferentes. A comparação
acontece apenas entre estratégias que resolvem o mesmo problema.

## As duas situações

Uma operação de I/O passa boa parte do tempo esperando algo externo, como rede,
disco ou banco de dados. Enquanto uma operação espera, o programa pode iniciar outra.

Uma operação que usa muita CPU passa o tempo executando cálculos. Nesse caso, não há
uma espera livre para ser aproveitada. Para executar vários cálculos ao mesmo tempo,
podem ser necessários processos separados.

No experimento de I/O, todas as estratégias simulam as mesmas dez operações externas,
com 250 milissegundos de espera em cada uma. No experimento de CPU, todas executam
os mesmos quatro cálculos, com cerca de 8 milhões de iterações por cálculo. Os
resultados só são comparados dentro de cada grupo.

## O que o experimento compara

| Situação | Estratégia | Comportamento |
| --- | --- | --- |
| Espera de I/O | sequencial | inicia a próxima operação depois que a anterior termina |
| Espera de I/O | `asyncio.gather` | inicia várias operações antes de aguardar os resultados |
| Espera de I/O | `time.sleep` | bloqueia o código assíncrono |
| Cálculo | execução direta | executa um cálculo depois do outro |
| Cálculo | `asyncio.to_thread` | envia os cálculos para threads |
| Cálculo | processos | executa os cálculos em processos separados |

As três estratégias de I/O recebem as mesmas operações e precisam devolver os mesmos
dez resultados. As três estratégias de CPU recebem os mesmos cálculos e precisam
devolver os mesmos quatro resultados. Assim, cada comparação muda apenas a forma de
execução, sem misturar os dois problemas.

## Como o bloqueio fica visível

O `event loop` coordena as tarefas assíncronas. Durante o experimento, uma pequena
tarefa tenta executar a cada 10 milissegundos. Ela funciona como um sinal periódico.
Se esse sinal atrasar muito, significa que o `event loop` ficou impedido de atender
outras tarefas.

## Preparação e execução

```bash
make setup
make check
make demo
```

`make demo` executa cada estratégia cinco vezes, mostra a mediana dos tempos e grava
os resultados completos em `output/results.json`. A demonstração leva cerca de 50
segundos neste ambiente.

A coluna `velocidade` compara cada estratégia com a execução básica do seu próprio
grupo. `10,00x`, por exemplo, significa que aquela estratégia terminou dez vezes
mais rápido. I/O continua sendo comparado apenas com I/O, e CPU apenas com CPU.

Uma execução local produziu valores próximos destes:

| Situação | Estratégia | Tempo mediano | Maior atraso do sinal |
| --- | --- | ---: | ---: |
| I/O | espera sequencial | 2,51 s | menos de 0,01 s |
| I/O | `asyncio.gather` | 0,25 s | menos de 0,01 s |
| I/O | `time.sleep` bloqueante | 2,58 s | 2,57 s |
| CPU | execução direta | 2,20 s | 2,20 s |
| CPU | `asyncio.to_thread` | 2,15 s | 0,14 s |
| CPU | processos | 0,71 s | 0,06 s |

Os números variam conforme o computador. O ponto importante é o comportamento:
`asyncio.gather` terminou as operações de I/O quase 10 vezes mais rápido, enquanto
`time.sleep` impediu o `event loop` de responder por 2,57 segundos. As threads não
aceleraram os cálculos, mas reduziram o atraso do sinal periódico. Os processos
terminaram estes cálculos cerca de 3 vezes mais rápido neste computador.

## Onde entra o GIL

No CPython tradicional, o GIL limita a execução simultânea de código Python em
threads. Por isso, enviar estes cálculos para `asyncio.to_thread` não reduziu o tempo
total. As threads ainda permitiram que o `event loop` atendesse outras tarefas com
mais frequência.

Processos possuem interpretadores separados e conseguem usar vários núcleos para
cálculos em Python. Em troca, custa tempo criar os processos e enviar dados para eles.

## Limite do laboratório

Este é um teste pequeno e local. Ele não determina qual estratégia será mais rápida
em produção, não compara linguagens e não representa cálculos de aprendizado de
máquina. A decisão real precisa ser medida com a carga e o ambiente do sistema.

## Resumo da ópera

I/O e CPU representam problemas diferentes e não competem entre si neste laboratório.
Cada grupo serve para comparar estratégias adequadas ao seu próprio tipo de problema.
Use código assíncrono quando várias operações passam tempo esperando I/O. Não execute
funções bloqueantes diretamente no `event loop`. Threads podem afastar essas funções
do código assíncrono, mas não garantem cálculos mais rápidos. Para executar cálculos
Python em paralelo, processos são uma opção, desde que o ganho compense seu custo.
