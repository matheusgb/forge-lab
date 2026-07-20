# Learning log

## Premissa

Uma instalação local com WSL2 x86_64, `pyenv` e `uv` representa a máquina limpa.
A remoção de `.venv` representa a perda de todos os pacotes instalados do projeto.

## Meta

Recriar o ambiente apenas a partir de `.python-version`, `pyproject.toml` e
`uv.lock`; depois executar lint, type check e testes sem erro.

## Medido

- Python: 3.14.6, selecionado pelo `.python-version` local.
- uv: 0.11.29.
- pyenv: 2.8.1.
- `make clean && make setup && make check`: passou; a `.venv` foi recriada pelo
  lock, Ruff e Pyright retornaram zero erros e os 2 testes passaram.
- falha de dependência ausente: detectada por `reportMissingImports`.
- falha de tipo: detectada por `reportAssignmentType`.

## Trade-off

Fixar o patch em `.python-version` aumenta a repetibilidade, mas a atualização não
é automática. A faixa `>=3.14,<3.15` em `pyproject.toml` comunica compatibilidade;
o pin local diz qual versão usamos para desenvolver e gerar a evidência.

## Próximo limite

Este laboratório prova recriação no ambiente local. Não prova publicação de pacote,
compatibilidade com múltiplos sistemas operacionais nem uma matriz de versões.
