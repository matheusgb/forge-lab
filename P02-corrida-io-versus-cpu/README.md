# P02: Corrida I/O versus CPU

Concorrência não acelera todo tipo de código da mesma forma. Esperar uma resposta da
rede é diferente de executar um cálculo pesado. Este laboratório compara estratégias
para os dois casos e mostra o que acontece quando uma função bloqueia o código
assíncrono.

## As duas situações

Uma operação de I/O passa boa parte do tempo esperando algo externo, como rede,
disco ou banco de dados. Enquanto uma operação espera, o programa pode iniciar outra.

Uma operação que usa muita CPU passa o tempo executando cálculos. Nesse caso, não há
uma espera livre para ser aproveitada. Para executar vários cálculos ao mesmo tempo,
podem ser necessários processos separados.

## O que o experimento compara

| Situação | Estratégia | Comportamento |
| --- | --- | --- |
| Espera de I/O | sequencial | inicia a próxima operação depois que a anterior termina |
| Espera de I/O | `asyncio.gather` | inicia várias operações antes de aguardar os resultados |
| Espera de I/O | `time.sleep` | bloqueia o código assíncrono |
| Cálculo | execução direta | executa um cálculo depois do outro |
| Cálculo | `asyncio.to_thread` | envia os cálculos para threads |
| Cálculo | processos | executa os cálculos em processos separados |

Todas as estratégias da mesma situação recebem os mesmos valores e precisam devolver
os mesmos resultados. Assim, a comparação mede apenas a forma de execução.

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
os resultados completos em `output/results.json`.

Uma execução local produziu valores próximos destes:

| Situação | Estratégia | Tempo mediano | Maior atraso do sinal |
| --- | --- | ---: | ---: |
| I/O | espera sequencial | 0,304 s | 0,0003 s |
| I/O | `asyncio.gather` | 0,031 s | 0,0003 s |
| I/O | `time.sleep` bloqueante | 0,301 s | 0,291 s |
| CPU | execução direta | 0,124 s | 0,117 s |
| CPU | `asyncio.to_thread` | 0,128 s | 0,048 s |
| CPU | processos | 0,045 s | 0,051 s |

Os números variam conforme o computador. O ponto importante é o comportamento:
`asyncio.gather` aproveitou o tempo de espera, enquanto `time.sleep` impediu o
`event loop` de responder. Os processos foram mais rápidos para estes cálculos neste
computador, mas também possuem custo de criação e comunicação.

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

Use código assíncrono quando várias operações passam tempo esperando I/O. Não execute
funções bloqueantes diretamente no `event loop`. Threads podem afastar essas funções
do código assíncrono, mas não garantem cálculos mais rápidos. Para executar cálculos
Python em paralelo, processos são uma opção, desde que o ganho compense seu custo.
