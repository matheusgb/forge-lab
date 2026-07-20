# P00 — Ambiente reproduzível

Um microprojeto para observar como versão do Python, ambiente virtual, dependências,
lockfile e ferramentas de qualidade se encaixam.

## Hipótese

Com a versão do Python fixada e `uv.lock` versionado, uma máquina limpa consegue
recriar o mesmo ambiente com um comando e executar os mesmos gates.

## Pré-requisitos

- `pyenv` para instalar e selecionar o Python indicado em `.python-version`;
- `uv` para criar `.venv`, resolver dependências e executar comandos.

Na raiz deste projeto, confira:

```bash
python --version
uv --version
pyenv version
```

O resultado esperado é Python 3.14.6 selecionado por esta pasta. O Python global
não precisa ser alterado.

## Execução

```bash
make setup
make check
make demo
```

`make setup` cria `.venv` e instala exatamente o grafo registrado em `uv.lock`.
Não é necessário ativar o ambiente: `uv run` escolhe a `.venv` do projeto. Se
quiser ativá-lo manualmente, use `source .venv/bin/activate`.

## O papel de cada arquivo

- `.python-version`: é parecido com `.nvmrc`; seleciona o interpretador local.
- `pyproject.toml`: declara o projeto, a faixa de Python, dependências diretas e
  configuração das ferramentas. É o arquivo de intenção, parecido com
  `package.json`.
- `uv.lock`: registra as versões exatas e hashes de todo o grafo resolvido. É o
  retrato reproduzível, parecido com `package-lock.json` ou `pnpm-lock.yaml`.
- `.venv`: contém o interpretador e os pacotes instalados localmente; não entra no
  Git porque é reconstruído pelos dois arquivos anteriores.

`pytest`, `ruff` e `pyright` são dependências de desenvolvimento: ajudam a testar,
formatar/lintar e verificar tipos, mas não fazem parte da execução do programa.
O projeto não possui dependência de runtime além da biblioteca padrão.

## Experimento controlado

```bash
make experiment
```

O script executa o `pyright` contra duas fixtures deliberadamente inválidas: uma
tem uma dependência ausente e outra atribui `str` onde `int` é esperado. O
experimento só passa quando ambos os verificadores falham pelo motivo esperado.
Essas fixtures ficam fora do gate normal para o projeto permanecer saudável.

Para provar a recriação completa:

```bash
make clean
make setup
make check
```

## Demo de três minutos

1. Mostre as três versões do ambiente.
2. Rode `make clean && make setup && make check`.
3. Rode `make experiment` e aponte os dois erros detectados.
4. Compare `pyproject.toml`, `uv.lock` e `.venv` usando a seção acima.
