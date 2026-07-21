# Evidência: cenário `io-versus-cpu-local`

**Medido em:** 2026-07-20

**Ambiente:** Python 3.14.6, WSL2 x86_64, 32 CPUs lógicas visíveis

**Repetições:** 5

| Categoria | Estratégia | Mediana do tempo total | Maior atraso do sinal | Velocidade relativa |
| --- | --- | ---: | ---: | ---: |
| I/O | espera sequencial | 2,51 s | menos de 0,01 s | 1,00x |
| I/O | asyncio.gather | 0,25 s | menos de 0,01 s | 9,99x |
| I/O | time.sleep bloqueante | 2,58 s | 2,57 s | 0,97x |
| CPU | execução direta | 2,20 s | 2,20 s | 1,00x |
| CPU | asyncio.to_thread | 2,15 s | 0,14 s | 1,02x |
| CPU | processos | 0,71 s | 0,06 s | 3,09x |

## Observações

- As três estratégias de I/O devolveram os mesmos dez resultados.
- As três estratégias de CPU devolveram os mesmos quatro resultados.
- `asyncio.gather` coordenou as esperas sem bloquear o sinal periódico.
- `time.sleep` dentro da coroutine impediu o event loop de responder por quase todo
  o tempo da execução.
- Threads permitiram que o event loop atendesse outras tarefas com mais frequência,
  mas não aceleraram estes cálculos em Python.
- Os processos tiveram a menor mediana neste hardware. A primeira execução demorou
  0,77 s, acima das demais (aproximadamente 0,71 s), porque também incluiu o tempo
  necessário para criar os processos.

Estes valores são resultado de laboratório, não uma previsão de produção.
