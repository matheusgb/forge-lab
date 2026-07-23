import time

from lifecycle_api.components import EventJournal


def run_background_job(
    job_id: str,
    duration_seconds: float,
    journal: EventJournal,
) -> None:
    journal.append("job_started", job_id=job_id)
    time.sleep(duration_seconds)
    journal.append("job_completed", job_id=job_id)
