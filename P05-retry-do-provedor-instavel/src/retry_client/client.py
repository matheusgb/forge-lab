from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from types import TracebackType

from httpx2 import BaseTransport, Client, Response, Timeout, TimeoutException

from retry_client.model import AttemptRecord, CallReport, Decision, Operation, RetryPolicy

Clock = Callable[[], datetime]
Wait = Callable[[float], None]
RandomValue = Callable[[], float]


@dataclass(frozen=True)
class TimeoutSettings:
    connect_seconds: float = 0.2
    read_seconds: float = 0.5
    write_seconds: float = 0.5
    pool_seconds: float = 0.2

    def as_httpx(self) -> Timeout:
        return Timeout(
            connect=self.connect_seconds,
            read=self.read_seconds,
            write=self.write_seconds,
            pool=self.pool_seconds,
        )


class RetryingProviderClient:
    def __init__(
        self,
        *,
        transport: BaseTransport,
        policy: RetryPolicy,
        timeout: TimeoutSettings,
        clock: Clock,
        wait: Wait,
        random_value: RandomValue,
    ) -> None:
        self.policy = policy
        self.clock = clock
        self.wait = wait
        self.random_value = random_value
        self.http = Client(
            base_url="https://provider.test",
            transport=transport,
            timeout=timeout.as_httpx(),
        )

    def __enter__(self) -> RetryingProviderClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        del exc_type, exc_value, traceback
        self.http.close()
        return False

    def call(self, operation: Operation) -> CallReport:
        records: list[AttemptRecord] = []
        for number in range(1, self.policy.max_attempts + 1):
            try:
                response = self.http.request(operation.method, "/resource")
            except TimeoutException:
                decision = self._decision(operation, number, transient=True)
                wait_seconds = self._wait_if_retry(number, decision, retry_after=None)
                records.append(AttemptRecord(number, "timeout", decision, wait_seconds))
                if decision is not Decision.RETRY_TRANSIENT:
                    return CallReport(operation, tuple(records), final_status=None)
                continue

            decision = self._response_decision(operation, number, response)
            retry_after = self._parse_retry_after(response)
            wait_seconds = self._wait_if_retry(number, decision, retry_after)
            records.append(
                AttemptRecord(
                    number,
                    f"http_{response.status_code}",
                    decision,
                    wait_seconds,
                )
            )
            if decision is not Decision.RETRY_TRANSIENT:
                return CallReport(operation, tuple(records), final_status=response.status_code)

        raise AssertionError("retry loop ended without a final decision")

    def _response_decision(
        self,
        operation: Operation,
        attempt_number: int,
        response: Response,
    ) -> Decision:
        if 200 <= response.status_code < 300:
            return Decision.SUCCESS
        transient = response.status_code == 429 or 500 <= response.status_code < 600
        if not transient:
            return Decision.STOP_PERMANENT
        return self._decision(operation, attempt_number, transient=True)

    def _decision(
        self,
        operation: Operation,
        attempt_number: int,
        *,
        transient: bool,
    ) -> Decision:
        if not transient:
            return Decision.STOP_PERMANENT
        if not operation.retry_safe:
            return Decision.STOP_UNSAFE
        if attempt_number >= self.policy.max_attempts:
            return Decision.STOP_EXHAUSTED
        return Decision.RETRY_TRANSIENT

    def _wait_if_retry(
        self,
        attempt_number: int,
        decision: Decision,
        retry_after: float | None,
    ) -> float | None:
        if decision is not Decision.RETRY_TRANSIENT:
            return None
        delay = self._backoff_with_jitter(attempt_number)
        if retry_after is not None:
            delay = max(delay, retry_after)
        self.wait(delay)
        return delay

    def _backoff_with_jitter(self, attempt_number: int) -> float:
        base = min(
            self.policy.base_delay_seconds * (2 ** (attempt_number - 1)),
            self.policy.max_delay_seconds,
        )
        random_value = self.random_value()
        if not 0 <= random_value <= 1:
            raise ValueError("random value must be between zero and one")
        jitter = base * self.policy.jitter_ratio * random_value
        return min(base + jitter, self.policy.max_delay_seconds)

    def _parse_retry_after(self, response: Response) -> float | None:
        value = response.headers.get("Retry-After")
        if value is None:
            return None
        try:
            seconds = float(value)
        except ValueError:
            return self._retry_after_date(value)
        return max(0.0, seconds)

    def _retry_after_date(self, value: str) -> float | None:
        try:
            retry_at = parsedate_to_datetime(value)
        except TypeError, ValueError:
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        return max(0.0, (retry_at - self.clock()).total_seconds())
