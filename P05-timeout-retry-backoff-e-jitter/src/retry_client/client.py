from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from httpx2 import Client, Response, TimeoutException
from tenacity import (
    RetryCallState,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from retry_client.model import CallResult, Decision, Operation, RetryPolicy

Clock = Callable[[], datetime]
Wait = Callable[[float], None]
RandomValue = Callable[[], float]


class TransientResponseError(Exception):
    def __init__(self, response: Response) -> None:
        self.response = response
        super().__init__(f"transient HTTP status: {response.status_code}")


class RetryingProviderClient:
    def __init__(
        self,
        *,
        http: Client,
        policy: RetryPolicy,
        clock: Clock,
        wait: Wait,
        random_value: RandomValue,
    ) -> None:
        self.http = http
        self.policy = policy
        self.clock = clock
        self.wait = wait
        self.random_value = random_value
        self.backoff = wait_exponential(
            multiplier=policy.base_delay_seconds,
            min=policy.base_delay_seconds,
            max=policy.max_delay_seconds,
        )

    def call(self, operation: Operation) -> CallResult:
        if not operation.retry_safe:
            return self._call_once(operation)

        retrying = Retrying(
            stop=stop_after_attempt(self.policy.max_attempts),
            retry=retry_if_exception_type((TimeoutException, TransientResponseError)),
            wait=self._wait_seconds,
            sleep=self.wait,
            reraise=True,
        )
        try:
            response = retrying(self._request_safe, operation)
        except (TimeoutException, TransientResponseError) as error:
            status_code = (
                error.response.status_code if isinstance(error, TransientResponseError) else None
            )
            return CallResult(operation, Decision.STOP_EXHAUSTED, status_code)

        return CallResult(
            operation,
            self._terminal_decision(response),
            response.status_code,
        )

    def _call_once(self, operation: Operation) -> CallResult:
        try:
            response = self.http.request(operation.method, "/resource")
        except TimeoutException:
            return CallResult(operation, Decision.STOP_UNSAFE, None)

        decision = (
            Decision.STOP_UNSAFE
            if self._is_transient(response)
            else self._terminal_decision(response)
        )
        return CallResult(operation, decision, response.status_code)

    def _request_safe(self, operation: Operation) -> Response:
        response = self.http.request(operation.method, "/resource")
        if self._is_transient(response):
            raise TransientResponseError(response)
        return response

    @staticmethod
    def _is_transient(response: Response) -> bool:
        return response.status_code == 429 or 500 <= response.status_code < 600

    @staticmethod
    def _terminal_decision(response: Response) -> Decision:
        if 200 <= response.status_code < 300:
            return Decision.SUCCESS
        return Decision.STOP_PERMANENT

    def _wait_seconds(self, state: RetryCallState) -> float:
        base = self.backoff(state)
        random_value = self.random_value()
        if not 0 <= random_value <= 1:
            raise ValueError("random value must be between zero and one")
        delay = min(
            base + base * self.policy.jitter_ratio * random_value,
            self.policy.max_delay_seconds,
        )
        retry_after = self._retry_after(state)
        return max(delay, retry_after) if retry_after is not None else delay

    def _retry_after(self, state: RetryCallState) -> float | None:
        if state.outcome is None:
            return None
        error = state.outcome.exception()
        if not isinstance(error, TransientResponseError):
            return None
        value = error.response.headers.get("Retry-After")
        if value is None:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            return self._retry_after_date(value)

    def _retry_after_date(self, value: str) -> float | None:
        try:
            retry_at = parsedate_to_datetime(value)
        except TypeError, ValueError:
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        return max(0.0, (retry_at - self.clock()).total_seconds())
