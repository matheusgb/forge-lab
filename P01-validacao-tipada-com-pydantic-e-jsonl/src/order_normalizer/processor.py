from collections import Counter
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path

from order_normalizer.errors import ErrorCode, OutputWriteError, RejectedLine
from order_normalizer.models import RejectedRecord
from order_normalizer.normalizer import normalize_line
from order_normalizer.output import write_json_line


@dataclass
class Summary:
    total: int = 0
    valid: int = 0
    rejected: int = 0
    errors: Counter[ErrorCode] = field(default_factory=Counter[ErrorCode])

    def record_valid(self) -> None:
        self.total += 1
        self.valid += 1

    def record_rejection(self, code: ErrorCode) -> None:
        self.total += 1
        self.rejected += 1
        self.errors[code] += 1

    def assert_invariant(self) -> None:
        if self.total != self.valid + self.rejected:
            raise AssertionError("total must equal valid plus rejected")


def process_file(input_path: Path, valid_path: Path, rejected_path: Path) -> Summary:
    summary = Summary()
    seen_order_ids: set[str] = set()

    with input_path.open(encoding="utf-8") as source, ExitStack() as outputs:
        try:
            valid_path.parent.mkdir(parents=True, exist_ok=True)
            rejected_path.parent.mkdir(parents=True, exist_ok=True)
            valid_output = outputs.enter_context(valid_path.open("w", encoding="utf-8"))
            rejected_output = outputs.enter_context(rejected_path.open("w", encoding="utf-8"))
        except OSError as error:
            destination = f"{valid_path} or {rejected_path}"
            raise OutputWriteError(destination, line_number=0) from error

        for line_number, raw_line in enumerate(source, start=1):
            try:
                order = normalize_line(raw_line, line_number)
                if order.order_id in seen_order_ids:
                    raise RejectedLine(
                        ErrorCode.DUPLICATE_ID,
                        f"duplicate order_id: {order.order_id}",
                        line_number=line_number,
                        field="order_id",
                    )
            except RejectedLine as error:
                rejection = RejectedRecord(
                    line=line_number,
                    code=error.code,
                    field=error.field,
                    message=str(error),
                    raw=raw_line.rstrip("\n"),
                )
                write_json_line(
                    rejected_output,
                    rejection,
                    destination=str(rejected_path),
                    line_number=line_number,
                )
                summary.record_rejection(error.code)
                continue

            write_json_line(
                valid_output,
                order,
                destination=str(valid_path),
                line_number=line_number,
            )
            seen_order_ids.add(order.order_id)
            summary.record_valid()

    summary.assert_invariant()
    return summary
