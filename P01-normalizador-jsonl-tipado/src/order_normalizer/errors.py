from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_JSON = "invalid_json"
    MISSING_FIELD = "missing_field"
    INVALID_FIELD = "invalid_field"
    UNKNOWN_CURRENCY = "unknown_currency"
    INVALID_DATE = "invalid_date"
    DUPLICATE_ID = "duplicate_id"
    OUTPUT_WRITE_ERROR = "output_write_error"


class RejectedLine(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        line_number: int,
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.line_number = line_number
        self.field = field


class OutputWriteError(Exception):
    code = ErrorCode.OUTPUT_WRITE_ERROR

    def __init__(self, destination: str, *, line_number: int) -> None:
        super().__init__(f"could not write output: {destination}")
        self.destination = destination
        self.line_number = line_number
