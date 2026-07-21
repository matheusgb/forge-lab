# Evidência: cenário `io-versus-cpu-local`

**Medido em:** 2026-07-20

**Ambiente:** Python 3.14.6, WSL2 x86_64, 32 CPUs lógicas visíveis

**Repetições:** 5

| Categoria | Estratégia | Mediana do tempo total | Maior atraso do sinal periódico |
| --- | --- | ---: | ---: |
| I/O | espera sequencial | 0,3043 s | 0,0003 s |
| I/O | asyncio.gather | 0,0306 s | 0,0003 s |
| I/O | time.sleep bloqueante | 0,3012 s | 0,2914 s |
| CPU | execução direta | 0,1241 s | 0,1166 s |
| CPU | asyncio.to_thread | 0,1282 s | 0,0477 s |
| CPU | processos | 0,0450 s | 0,0510 s |

## Observações

- As três estratégias de I/O devolveram os mesmos dez resultados.
- As três estratégias de CPU devolveram os mesmos quatro resultados.
- `asyncio.gather` coordenou as esperas sem bloquear o sinal periódico.
- `time.sleep` dentro da coroutine impediu o event loop de responder por quase todo
  o tempo da execução.
- Threads permitiram que o event loop atendesse outras tarefas com mais frequência,
  mas não aceleraram estes cálculos em Python.
- Os processos tiveram a menor mediana neste hardware. A primeira execução demorou
  0,1019 s, acima das demais (aproximadamente 0,045 s), porque também incluiu o tempo
  necessário para criar os processos.

Estes valores são resultado de laboratório, não uma previsão de produção.
