# Registro de aprendizado

## Premissa

Dez chamadas de `sleep` simulam operações independentes que esperam I/O. Quatro
laços aritméticos simulam cálculos que usam a CPU. Cada estratégia recebe os mesmos
valores de entrada em cinco repetições.

## Meta

Observar `gather` coordenando várias esperas, uma chamada bloqueante atrasando o
sinal periódico e threads ou processos mudando o tempo e a capacidade de resposta.

## Medido

- ambiente: Python 3.14.6, WSL2 x86_64, 32 CPUs lógicas visíveis.
- I/O sequencial: mediana de 2,51 s; sinal periódico atrasou menos de 0,01 s.
- I/O concorrente: mediana de 0,25 s; sinal periódico atrasou menos de 0,01 s.
- I/O bloqueante: mediana de 2,58 s; sinal periódico atrasou 2,57 s.
- Cálculo direto: 2,20 s; com `to_thread`: 2,15 s; com processos: 0,71 s.
- Verificação: resultados iguais por categoria, 5 testes passaram, Ruff e Pyright
  não encontraram erros.

Neste ambiente, `to_thread` permitiu que o sinal periódico fosse atendido com mais
frequência, mas não acelerou os cálculos em Python. Os processos apresentaram a
menor mediana. A primeira repetição com processos demorou 0,77 s e as seguintes
ficaram próximas de 0,71 s.

## Escolha e consequência

Toda forma de concorrência possui um custo. Antes de escolher uma estratégia, é
preciso saber se o código está esperando uma operação externa ou usando a CPU. A
mediana de cinco execuções reduz variações, mas este teste pequeno ainda não prevê o
comportamento de um sistema em produção.

## Próximo limite

O conjunto de processos é recriado em cada repetição para manter o experimento
simples. Portanto, parte do tempo medido corresponde à criação desses processos. Um
serviço real normalmente reutilizaria o mesmo executor.
