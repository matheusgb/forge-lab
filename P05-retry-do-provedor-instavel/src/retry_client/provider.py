from dataclasses import dataclass

from httpx2 import MockTransport, ReadTimeout, Request, Response


@dataclass(frozen=True)
class Outcome:
    status_code: int | None = None
    headers: tuple[tuple[str, str], ...] = ()
    times_out: bool = False

    @classmethod
    def response(
        cls,
        status_code: int,
        *,
        retry_after: str | None = None,
    ) -> Outcome:
        headers = () if retry_after is None else (("Retry-After", retry_after),)
        return cls(status_code=status_code, headers=headers)

    @classmethod
    def timeout(cls) -> Outcome:
        return cls(times_out=True)


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
            headers=dict(outcome.headers),
            json={"attempt": self.attempts},
            request=request,
        )

    def transport(self) -> MockTransport:
        return MockTransport(self.handle)
