import json
from pathlib import Path
from typing import Annotated

import typer

from order_normalizer.errors import OutputWriteError
from order_normalizer.processor import process_file


def normalize_orders(
    input_path: Annotated[Path, typer.Argument(help="Arquivo JSONL de entrada")],
    valid_path: Annotated[Path, typer.Argument(help="Saída com pedidos válidos")],
    rejected_path: Annotated[Path, typer.Argument(help="Saída com linhas rejeitadas")],
) -> None:
    try:
        summary = process_file(input_path, valid_path, rejected_path)
    except OutputWriteError as error:
        typer.echo(f"output error: {error}", err=True)
        raise typer.Exit(code=1) from error

    typer.echo(
        json.dumps(
            {
                "total": summary.total,
                "valid": summary.valid,
                "rejected": summary.rejected,
                "invariant": summary.total == summary.valid + summary.rejected,
            },
            separators=(",", ":"),
        )
    )


def main() -> None:
    typer.run(normalize_orders)
