import json
from pathlib import Path

from task_api.app import create_app


def main() -> None:
    schema = create_app().openapi()
    output = Path("evidence/openapi.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OpenAPI saved to {output}")


if __name__ == "__main__":
    main()
