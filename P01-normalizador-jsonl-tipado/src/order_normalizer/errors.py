from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_JSON = "invalid_json"
    MISSING_FIELD = "missing_field"
    INVALID_FIELD = "invalid_field"
    UNKNOWN_CURRENCY = "unknown_currency"
    INVALID_DATE = "invalid_date"
    DUPLICATE_ID = "duplicate_id"
    OUTPUT_WRITE_ERROR = "output_write_error"


class NormalizationError(Exception):
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


class InvalidJsonError(NormalizationError):
    def __init__(self, *, line_number: int) -> None:
        super().__init__(ErrorCode.INVALID_JSON, "line is not valid JSON", line_number=line_number)


class MissingFieldError(NormalizationError):
    def __init__(self, field: str, *, line_number: int) -> None:
        super().__init__(
            ErrorCode.MISSING_FIELD,
            f"required field is missing: {field}",
            line_number=line_number,
            field=field,
        )


class InvalidFieldError(NormalizationError):
    def __init__(self, field: str, message: str, *, line_number: int) -> None:
        super().__init__(
            ErrorCode.INVALID_FIELD,
            message,
            line_number=line_number,
            field=field,
        )


class UnknownCurrencyError(NormalizationError):
    def __init__(self, currency: str, *, line_number: int) -> None:
        super().__init__(
            ErrorCode.UNKNOWN_CURRENCY,
            f"unknown currency: {currency}",
            line_number=line_number,
            field="currency",
        )


class InvalidDateError(NormalizationError):
    def __init__(self, value: str, *, line_number: int) -> None:
        super().__init__(
            ErrorCode.INVALID_DATE,
            f"invalid ISO 8601 date: {value}",
            line_number=line_number,
            field="created_at",
        )


class DuplicateOrderError(NormalizationError):
    def __init__(self, order_id: str, *, line_number: int) -> None:
        super().__init__(
            ErrorCode.DUPLICATE_ID,
            f"duplicate order_id: {order_id}",
            line_number=line_number,
            field="order_id",
        )


class OutputWriteError(NormalizationError):
    def __init__(self, destination: str, *, line_number: int) -> None:
        super().__init__(
            ErrorCode.OUTPUT_WRITE_ERROR,
            f"could not write output: {destination}",
            line_number=line_number,
        )
