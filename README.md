# Expense Tracker: REST API + AI Agent

Two small services in one repo:

| Folder | What it is |
|---|---|
| `expense-tracker-service/` | FastAPI + SQLAlchemy + Alembic backend that owns users and expenses, with reports and an admin console. |
| `expense-tracker-agent/` | FastAPI chat agent. It turns messages like "I paid 250 for lunch at Starbucks" into calls to the backend, using an LLM with tool calling (OpenAI today, pluggable providers). |

```
Browser chat page ──> agent (:8000) ──LLM tool calls──> backend API (:8001) ──> database
```

## How the agent works
1. `intent_classifier` decides whether the message is about expenses or not.
2. Off-topic messages get a short reply (`direct_agent`); expense messages go to the `planner`.
3. The planner lets the LLM call 5 tools: `list_expenses`, `create_expense`, `update_expense`, `delete_expense`, `get_summary`.
4. `user_id` is injected by the code, never by the LLM. Update/delete also check the expense belongs to the user.
5. Recent chat turns are stored per session (SQLite) so follow-ups like "change that to 300" work.

LLM settings live in the provider (`app/llm/config.py`), so each provider owns its own env vars.

## Run locally (Python 3.12+)

Backend:
```bash
cd expense-tracker-service
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
sh scripts/start.sh                                   # migrate + demo data + server on :8001 (docs at /docs, console at /console/)
```

Agent:
```bash
cd expense-tracker-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                                  # add your OPENAI_API_KEY
uvicorn app.main:app --port 8000                      # chat UI at http://localhost:8000/
```

More detail on the backend (layout, migrations, tests, load-test data) is in `expense-tracker-service/README.md`.

## Demo data
- Backend: `scripts/seed.sql` holds 10 users and ~110 expenses. `scripts/start.sh` runs migrations and loads it only if the database is empty, so every redeploy starts with fresh demo data.
- Agent: `app/history.py` seeds three sample chats (sessions `demo-1`..`demo-3`, users 1-3) when its history DB is empty.
- Regenerate the backend seed: `python scripts/generate_seed.py --seed 7 --users 10 --max-expenses 12`.

## Hosting (free tier, e.g. Render)
Both services use SQLite on a throwaway disk, which is fine because they re-seed on every start.

| | Backend (`expense-tracker-service`) | Agent (`expense-tracker-agent`) |
|---|---|---|
| Build | `pip install -r requirements.txt` | `pip install -r requirements.txt` |
| Start | `sh scripts/start.sh` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Env | none needed | `OPENAI_API_KEY`, `BACKEND_URL=https://<backend-host>/api/v1` |

## Known limitations
- No authentication: the chat UI asks for a user ID. Demo only; set a spending cap on your OpenAI key.
- Data resets on redeploy (by design).
