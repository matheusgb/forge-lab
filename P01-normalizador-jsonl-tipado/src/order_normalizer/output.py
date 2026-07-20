import json
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from order_normalizer.errors import NormalizationError, OutputWriteError
from order_normalizer.models import Order


@dataclass(frozen=True)
class OutputStreams:
    valid: TextIO
    rejected: TextIO


def order_payload(order: Order) -> dict[str, object]:
    return {
        "order_id": order.order_id,
        "created_at": order.created_at.isoformat().replace("+00:00", "Z"),
        "amount": str(order.total.amount),
        "currency": order.total.currency.value,
        "tags": list(order.tags),
        "note": order.note,
    }


def rejection_payload(error: NormalizationError, raw_line: str) -> dict[str, object]:
    return {
        "line": error.line_number,
        "code": error.code.value,
        "field": error.field,
        "message": str(error),
        "raw": raw_line.rstrip("\n"),
    }


def write_json_line(
    stream: TextIO,
    payload: Mapping[str, object],
    *,
    destination: str,
    line_number: int,
) -> None:
    try:
        stream.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    except OSError as error:
        raise OutputWriteError(destination, line_number=line_number) from error


@contextmanager
def open_outputs(valid_path: Path, rejected_path: Path) -> Generator[OutputStreams]:
    try:
        valid_path.parent.mkdir(parents=True, exist_ok=True)
        rejected_path.parent.mkdir(parents=True, exist_ok=True)
        with (
            valid_path.open("w", encoding="utf-8") as valid,
            rejected_path.open("w", encoding="utf-8") as rejected,
        ):
            yield OutputStreams(valid, rejected)
    except OSError as error:
        raise OutputWriteError(f"{valid_path} or {rejected_path}", line_number=0) from error
