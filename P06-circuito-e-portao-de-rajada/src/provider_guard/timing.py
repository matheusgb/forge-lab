from collections.abc import Callable

Clock = Callable[[], float]


class ManualClock:
    def __init__(self, initial_seconds: float = 0.0) -> None:
        self._seconds = initial_seconds

    def __call__(self) -> float:
        return self._seconds

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("time advance must not be negative")
        self._seconds += seconds
