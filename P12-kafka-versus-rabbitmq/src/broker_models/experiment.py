from pathlib import Path

from broker_models.comparison import render_report
from broker_models.kafka_demo import run_kafka
from broker_models.model import ExperimentResult, Scenario
from broker_models.rabbit_demo import run_rabbit


async def run_experiment(project: Path, *, write_evidence: bool = True) -> ExperimentResult:
    scenario = Scenario.load(project / "scenario.yaml")
    produced, consumed, replayed, live_group_resumed_at_end = await run_kafka(scenario)
    rabbit = await run_rabbit(scenario)
    result = ExperimentResult(
        kafka_topic=scenario.kafka_topic,
        kafka_produced=produced,
        kafka_consumed=consumed,
        kafka_replayed=replayed,
        kafka_live_group_resumed_at_end=live_group_resumed_at_end,
        rabbit=rabbit,
    )
    if write_evidence:
        report = render_report(result)
        (project / "evidence" / "result.txt").write_text(f"{report}\n", encoding="utf-8")
    return result
