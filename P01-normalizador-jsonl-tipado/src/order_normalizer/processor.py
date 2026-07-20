from dataclasses import dataclass, field
from pathlib import Path

from order_normalizer.errors import DuplicateOrderError, ErrorCode
from order_normalizer.normalizer import normalize_line
from order_normalizer.output import (
    open_outputs,
    order_payload,
    rejection_payload,
    write_json_line,
)


def _empty_error_counts() -> dict[ErrorCode, int]:
    return {}


@dataclass
class Summary:
    total: int = 0
    valid: int = 0
    rejected: int = 0
    errors: dict[ErrorCode, int] = field(default_factory=_empty_error_counts)

    def record_valid(self) -> None:
        self.total += 1
        self.valid += 1

    def record_rejection(self, code: ErrorCode) -> None:
        self.total += 1
        self.rejected += 1
        self.errors[code] = self.errors.get(code, 0) + 1

    def assert_invariant(self) -> None:
        if self.total != self.valid + self.rejected:
            raise AssertionError("total must equal valid plus rejected")


def process_file(input_path: Path, valid_path: Path, rejected_path: Path) -> Summary:
    summary = Summary()
    seen_order_ids: set[str] = set()

    with (
        input_path.open(encoding="utf-8") as source,
        open_outputs(valid_path, rejected_path) as outputs,
    ):
        for line_number, raw_line in enumerate(source, start=1):
            result = normalize_line(raw_line, line_number)
            error = result.error
            order = result.value

            if error is None and order is not None and order.order_id in seen_order_ids:
                error = DuplicateOrderError(order.order_id, line_number=line_number)
                order = None

            if error is not None:
                write_json_line(
                    outputs.rejected,
                    rejection_payload(error, raw_line),
                    destination=str(rejected_path),
                    line_number=line_number,
                )
                summary.record_rejection(error.code)
                continue

            if order is None:
                raise AssertionError("successful result must contain an order")

            write_json_line(
                outputs.valid,
                order_payload(order),
                destination=str(valid_path),
                line_number=line_number,
            )
            seen_order_ids.add(order.order_id)
            summary.record_valid()

    summary.assert_invariant()
    return summary
