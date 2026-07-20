import json
from pathlib import Path
from typing import TextIO, cast

import pytest

from order_normalizer.errors import ErrorCode, OutputWriteError
from order_normalizer.output import write_json_line
from order_normalizer.processor import process_file


class BrokenStream:
    def write(self, value: str) -> int:
        raise OSError("disk full")


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_mixed_file_classifies_every_line(tmp_path: Path) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "orders-mixed.jsonl"
    valid_path = tmp_path / "valid.jsonl"
    rejected_path = tmp_path / "rejected.jsonl"

    summary = process_file(fixture, valid_path, rejected_path)

    assert (summary.total, summary.valid, summary.rejected) == (6, 2, 4)
    assert summary.total == summary.valid + summary.rejected
    assert set(summary.errors) == {
        ErrorCode.UNKNOWN_CURRENCY,
        ErrorCode.INVALID_DATE,
        ErrorCode.MISSING_FIELD,
        ErrorCode.INVALID_JSON,
    }
    assert len(read_jsonl(valid_path)) == 2
    assert len(read_jsonl(rejected_path)) == 4


def test_duplicate_order_is_rejected(tmp_path: Path) -> None:
    line = '{"order_id":"same","created_at":"2026-07-20T10:00:00Z","amount":1,"currency":"BRL"}\n'
    source = tmp_path / "input.jsonl"
    source.write_text(line + line, encoding="utf-8")

    summary = process_file(source, tmp_path / "valid.jsonl", tmp_path / "rejected.jsonl")

    assert (summary.valid, summary.rejected) == (1, 1)
    assert summary.errors == {ErrorCode.DUPLICATE_ID: 1}


def test_output_error_preserves_os_error_as_cause() -> None:
    stream = cast(TextIO, BrokenStream())

    with pytest.raises(OutputWriteError) as captured:
        write_json_line(stream, {"ok": True}, destination="broken", line_number=3)

    assert captured.value.code is ErrorCode.OUTPUT_WRITE_ERROR
    assert captured.value.line_number == 3
    assert isinstance(captured.value.__cause__, OSError)
