# Evidências do experimento

O comando `uv run python scripts/run_experiment.py` recria os arquivos desta pasta.

`result.txt` resume o ambiente, os scans escolhidos, o número de consultas e o tamanho
da serialização local. A pasta `plans/` preserva cada `EXPLAIN (ANALYZE, BUFFERS)` em
texto legível e em JSON com os campos usados pelo experimento.

Os valores são medições locais. Eles não representam uma meta de desempenho nem uma
estimativa de produção.
