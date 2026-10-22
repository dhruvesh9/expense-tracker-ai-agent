"""How another Python project (e.g. the agent) can call this backend over HTTP.

Run the backend first (port 8001), then:  python examples/agent_client_example.py
Only needs ``httpx``; it shares no code, models or database with the backend.
"""

import httpx

BASE_URL = "http://127.0.0.1:8001/api/v1"


def main() -> None:
    # One Client reuses connections; the timeout stops a hung backend blocking forever.
    with httpx.Client(base_url=BASE_URL, timeout=5.0) as client:
        user = client.post("/users", json={"name": "Demo User"}).json()

        # "Add a 250 rupee lunch expense for yesterday" -> structured call:
        response = client.post(
            "/expenses",
            json={
                "user_id": user["id"],
                "amount": "250",  # send money as a string/decimal, never compute with floats
                "description": "Lunch",
                "category": "food",
                "expense_date": "2026-10-18",
            },
        )
        if response.status_code >= 400:
            # Every error has the same shape: {"error": {"code", "message", "details", "request_id"}}
            print("failed:", response.json()["error"])
            return
        print("created:", response.json())

        print("summary:", client.get("/reports/summary", params={"user_id": user["id"]}).json())


if __name__ == "__main__":
    main()
