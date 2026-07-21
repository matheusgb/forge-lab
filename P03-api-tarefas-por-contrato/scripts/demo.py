from typing import cast

from fastapi.testclient import TestClient
from httpx2 import Client

from task_api.app import create_app


def main() -> None:
    headers = {"X-User-ID": "demo-user", "X-Request-ID": "demo-request"}
    with TestClient(create_app()) as test_client:
        client = cast(Client, test_client)
        created = client.post(
            "/tasks",
            headers=headers,
            json={"title": "Entender Depends", "description": "Concluir o P03"},
        )
        task_id = created.json()["id"]
        found = client.get(f"/tasks/{task_id}", headers=headers)
        completed = client.patch(f"/tasks/{task_id}/complete", headers=headers)
        repeated = client.patch(f"/tasks/{task_id}/complete", headers=headers)

    print("POST /tasks", created.status_code, created.json())
    print("GET /tasks/{id}", found.status_code, found.json())
    print("PATCH /tasks/{id}/complete", completed.status_code, completed.json())
    print("PATCH repetido", repeated.status_code, repeated.json())


if __name__ == "__main__":
    main()
