import argparse
from collections.abc import Sequence

from p00_ambiente_reproduzivel import greeting


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Confirma que o ambiente P00 funciona")
    parser.add_argument("name", help="nome exibido na saudação")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    print(greeting(args.name))
