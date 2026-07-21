from datetime import datetime


class RecordingWait:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


class FixedRandom:
    def __init__(self, value: float) -> None:
        if not 0 <= value <= 1:
            raise ValueError("random value must be between zero and one")
        self.value = value

    def __call__(self) -> float:
        return self.value


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value
