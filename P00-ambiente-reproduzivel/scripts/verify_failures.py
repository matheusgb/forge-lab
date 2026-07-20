from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class ExpectedFailure:
    label: str
    command: tuple[str, ...]
    expected_text: str


def verify(case: ExpectedFailure) -> None:
    result = subprocess.run(case.command, capture_output=True, check=False, text=True)
    output = f"{result.stdout}\n{result.stderr}"

    if result.returncode == 0:
        raise RuntimeError(f"{case.label}: o comando deveria falhar")
    if case.expected_text not in output:
        raise RuntimeError(
            f"{case.label}: falhou por motivo inesperado\nSaída recebida:\n{output}"
        )

    print(f"[falha esperada] {case.label}")
    print(output.strip())


def main() -> None:
    cases = (
        ExpectedFailure(
            label="dependência ausente",
            command=("pyright", "--project", "experiments/pyright-missing.json"),
            expected_text="reportMissingImports",
        ),
        ExpectedFailure(
            label="tipo incompatível",
            command=("pyright", "--project", "experiments/pyright-type.json"),
            expected_text="reportAssignmentType",
        ),
    )
    for case in cases:
        verify(case)


if __name__ == "__main__":
    main()
