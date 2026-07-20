import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from order_normalizer.errors import OutputWriteError
from order_normalizer.processor import process_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normaliza pedidos JSONL")
    parser.add_argument("input", type=Path, help="arquivo JSONL de entrada")
    parser.add_argument("valid", type=Path, help="saída com pedidos válidos")
    parser.add_argument("rejected", type=Path, help="saída com linhas rejeitadas")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        summary = process_file(args.input, args.valid, args.rejected)
    except OutputWriteError as error:
        raise SystemExit(f"output error: {error}") from error

    print(
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
