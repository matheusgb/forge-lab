# P00: Ambiente reproduzível

Este projeto mostra como recriar um ambiente Python sem depender dos pacotes que já
estão instalados na máquina.

## Como o programa funciona

O projeto registra a versão do Python, as dependências e as ferramentas de qualidade.
O `uv` usa esses arquivos para criar a `.venv`, instalar as versões corretas e executar
lint, verificação de tipos e testes.

```text
.python-version + pyproject.toml + uv.lock
                    |
                    v
          ambiente virtual novo
                    |
                    v
          lint + tipos + testes
```

O ambiente virtual pode ser apagado porque ele é apenas o resultado desses arquivos.

## Conceito abordado

O conceito é a reprodutibilidade do ambiente. Um ambiente é reproduzível quando outra
pessoa consegue instalar as mesmas versões e executar as mesmas verificações a partir
dos arquivos versionados no Git.

O Typer representa uma dependência direta, pois a aplicação precisa dele para executar
a CLI. Ruff, Pyright e pytest são dependências de desenvolvimento, pois eles verificam
o projeto, mas não participam da execução da aplicação.

| Arquivo | Função |
| --- | --- |
| `.python-version` | seleciona o Python usado nesta pasta |
| `pyproject.toml` | declara o projeto, as dependências diretas e as ferramentas |
| `uv.lock` | fixa as versões exatas dos pacotes instalados |
| `.venv` | guarda o ambiente gerado e não entra no Git |

## Para que isso serve em produção

Uma equipe precisa executar o mesmo código em notebooks, integração contínua e
containers. Versões diferentes podem mudar o comportamento do programa ou quebrar o
deploy.

Exemplo: uma biblioteca publica uma versão nova com uma mudança incompatível. Um
projeto sem lock instala essa versão automaticamente e a pipeline começa a falhar. Com
o `uv.lock`, todos continuam usando a versão validada até que a atualização seja feita
de forma explícita.

## Como executar

```bash
uv sync --locked
uv run ruff check .
uv run pyright
uv run pytest
uv run p00 ForgeLab
```

`uv sync --locked` cria a `.venv`. O `uv run` executa cada ferramenta nesse ambiente,
então não é necessário ativá-lo manualmente.

Para apagar o ambiente e provar que ele pode ser reconstruído:

```bash
rm -rf .venv .pytest_cache .ruff_cache
uv sync --locked
uv run ruff check .
uv run pyright
uv run pytest
```

## Falha controlada

```bash
uv run pyright --project experiments/pyright-missing.json
uv run pyright --project experiments/pyright-type.json
```

O experimento apresenta uma dependência ausente e uma atribuição de texto onde o código
espera um número. Cada comando deve terminar com falha e apontar, respectivamente,
`reportMissingImports` e `reportAssignmentType`. Os comandos ficam visíveis porque a
falha do verificador é o próprio objeto deste experimento.

## Resultado observado

No ambiente registrado em `evidence/environment.txt`, o projeto usou Python 3.14.6,
uv 0.11.29 e pyenv 2.8.1. A recriação da `.venv` passou pelo Ruff, pelo Pyright e por
dois testes. O Pyright também detectou as duas falhas controladas.

## Limite do projeto

O teste cobre apenas o ambiente local. Ele não comprova compatibilidade com outros
sistemas operacionais, várias versões do Python ou publicação de pacotes.

## Resumo da ópera

Os arquivos versionados definem o ambiente. A `.venv` é descartável. Em um projeto
real, essa separação reduz diferenças entre desenvolvimento, testes e deploy.
