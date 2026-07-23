from typing import Annotated

import typer

from p00_ambiente_reproduzivel import greeting


def greet(name: Annotated[str, typer.Argument(help="Nome exibido na saudação")]) -> None:
    print(greeting(name))


def main() -> None:
    typer.run(greet)
