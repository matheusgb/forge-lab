from typing import TextIO

from pydantic import BaseModel

from order_normalizer.errors import OutputWriteError


def write_json_line(
    stream: TextIO,
    record: BaseModel,
    *,
    destination: str,
    line_number: int,
) -> None:
    try:
        stream.write(record.model_dump_json() + "\n")
    except OSError as error:
        raise OutputWriteError(destination, line_number=line_number) from error
