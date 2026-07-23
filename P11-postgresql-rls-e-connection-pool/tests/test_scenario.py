from pathlib import Path

import pytest
from pydantic import ValidationError

from tenant_guard import load_scenario


def test_rejects_duplicate_tenant_ids(tmp_path: Path) -> None:
    scenario = tmp_path / "scenario.yaml"
    scenario.write_text(
        """
tenants:
  - id: "11111111-1111-4111-8111-111111111111"
    name: "Aurora"
    documents: ["a.txt"]
  - id: "11111111-1111-4111-8111-111111111111"
    name: "Boreal"
    documents: ["b.txt"]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="tenant ids must be unique"):
        load_scenario(scenario)
