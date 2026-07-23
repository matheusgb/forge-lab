from httpx2 import MockTransport, ReadTimeout, Request, Response
from pydantic import BaseModel, ConfigDict, Field


class Outcome(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    status_code: int | None = Field(default=None, validation_alias="status")
    retry_after: str | None = None
    times_out: bool = Field(default=False, validation_alias="timeout")

    @classmethod
    def response(
        cls,
        status_code: int,
        *,
        retry_after: str | None = None,
    ) -> Outcome:
        return cls(status_code=status_code, retry_after=retry_after)

    @classmethod
    def timeout(cls) -> Outcome:
        return cls(times_out=True)

    @property
    def label(self) -> str:
        return "timeout" if self.times_out else f"http_{self.status_code}"


class FakeProvider:
    def __init__(self, outcomes: tuple[Outcome, ...]) -> None:
        if not outcomes:
            raise ValueError("fake provider needs at least one outcome")
        self.outcomes = outcomes
        self.requests: list[Request] = []

    @property
    def attempts(self) -> int:
        return len(self.requests)

    def handle(self, request: Request) -> Response:
        self.requests.append(request)
        index = self.attempts - 1
        if index >= len(self.outcomes):
            raise AssertionError("fake provider received more requests than planned")

        outcome = self.outcomes[index]
        if outcome.times_out:
            raise ReadTimeout("controlled provider timeout", request=request)
        if outcome.status_code is None:
            raise AssertionError("response outcome has no status code")
        return Response(
            outcome.status_code,
            headers=(
                {"Retry-After": outcome.retry_after} if outcome.retry_after is not None else None
            ),
            json={"attempt": self.attempts},
            request=request,
        )

    def transport(self) -> MockTransport:
        return MockTransport(self.handle)
