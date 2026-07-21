# P00: Ambiente reproduzível

Um projeto Python pode funcionar na sua máquina e falhar em outra porque a versão do
Python ou das dependências é diferente. Este laboratório mostra como registrar essas
versões e recriar o mesmo ambiente quando necessário.

## O que este projeto comprova

O ambiente virtual `.venv` pode ser apagado sem medo. A versão do Python e as
dependências necessárias estão descritas em arquivos que permanecem no projeto.
Com esses arquivos, o `uv` consegue criar uma `.venv` nova e repetir as verificações.

## Preparação e execução

```bash
make setup
make check
make demo
```

`make setup` cria a `.venv` e instala as dependências. Não é necessário ativar o
ambiente manualmente porque os comandos usam `uv run`.

Para conferir as ferramentas usadas:

```bash
python --version
pyenv version
uv --version
```

Dentro desta pasta, o resultado esperado é Python 3.14.6. Essa escolha vale apenas
para o projeto e não altera a versão global do Python.

## O papel de cada arquivo

| Arquivo | Para que serve |
| --- | --- |
| `.python-version` | escolhe a versão do Python nesta pasta |
| `pyproject.toml` | descreve o projeto, as dependências diretas e as ferramentas |
| `uv.lock` | registra as versões exatas de todos os pacotes instalados |
| `.venv` | guarda o Python e os pacotes usados durante a execução |

Se você conhece JavaScript, `pyproject.toml` se parece com `package.json` e
`uv.lock` cumpre um papel parecido com `package-lock.json`. A `.venv` não entra no
Git porque pode ser reconstruída.

## Experimento

Primeiro, apague o ambiente e recrie tudo:

```bash
make clean
make setup
make check
```

Depois, confirme que as ferramentas também detectam código inválido:

```bash
make experiment
```

O experimento apresenta dois erros intencionais. Um arquivo importa uma dependência
que não existe. O outro coloca um texto onde o código espera um número inteiro. O
experimento só passa se o Pyright identificar os dois problemas.

## Limite do laboratório

Este projeto comprova a recriação do ambiente local. Ele não testa vários sistemas
operacionais, várias versões do Python nem a publicação de um pacote.

## Resumo da ópera

`.python-version` escolhe o Python. `pyproject.toml` declara o que o projeto precisa.
`uv.lock` registra as versões exatas. A `.venv` é apenas o ambiente criado a partir
desses arquivos. Se ela desaparecer, `uv sync --locked` consegue recriá-la.
