import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def test_step_by_step_shows_json_and_cursor_calls_in_order() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/run_experiment.py", "--step-by-step"],
        cwd=PROJECT,
        capture_output=True,
        text=True,
        check=True,
    )

    output = completed.stdout
    calls = (
        "Chamada: provider.get_page(cursor=None)",
        "Chamada: provider.get_page(cursor='Njo1')",
        "Chamada: provider.get_page(cursor='Njoz')",
    )
    call_positions = tuple(output.index(call) for call in calls)

    assert call_positions == tuple(sorted(call_positions))
    assert output.count("JSON recebido:") == 3
    assert '"next_cursor": "Njo1"' in output
    assert '"next_cursor": "Njoz"' in output
    assert "next_cursor recebido: null" in output
    assert "Decisão: o cliente encerra a paginação." in output
    assert "Resultado final: páginas=((6, 5), (4, 3), (2, 1)); itens=(6, 5, 4, 3, 2, 1)" in output
