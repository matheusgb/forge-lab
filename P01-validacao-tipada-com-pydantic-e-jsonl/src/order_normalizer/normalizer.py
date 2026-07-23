from pydantic import ValidationError

from order_normalizer.errors import ErrorCode, RejectedLine
from order_normalizer.models import Order


def _rejection_from(error: ValidationError, line_number: int) -> RejectedLine:
    issue = error.errors(include_url=False)[0]
    location = issue["loc"]
    field = str(location[0]) if location else None
    issue_type = issue["type"]
    received = issue.get("input")

    if issue_type == "json_invalid":
        return RejectedLine(
            ErrorCode.INVALID_JSON,
            "line is not valid JSON",
            line_number=line_number,
        )
    if issue_type == "missing":
        return RejectedLine(
            ErrorCode.MISSING_FIELD,
            f"required field is missing: {field}",
            line_number=line_number,
            field=field,
        )
    if field == "currency":
        return RejectedLine(
            ErrorCode.UNKNOWN_CURRENCY,
            f"unknown currency: {received}",
            line_number=line_number,
            field=field,
        )
    if field == "created_at":
        return RejectedLine(
            ErrorCode.INVALID_DATE,
            f"invalid ISO 8601 date: {received}",
            line_number=line_number,
            field=field,
        )
    return RejectedLine(
        ErrorCode.INVALID_FIELD,
        issue["msg"],
        line_number=line_number,
        field=field,
    )


def normalize_line(line: str, line_number: int) -> Order:
    try:
        return Order.model_validate_json(line)
    except ValidationError as error:
        raise _rejection_from(error, line_number) from error
