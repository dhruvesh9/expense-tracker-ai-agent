import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from app import backend_client, history
from app.agents import direct_agent, intent_classifier, planner, response_agent
from app.models import ChatRequest, ChatResponse

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    history.init_db()  # runs once when the server starts
    yield


app = FastAPI(title="Expense Tracker agent", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    
    user = backend_client.get_user(req.user_id)
    if "error" in user:
        raise HTTPException(status_code=404, detail="Unknown user")

    logging.info(f"User details === {user}")

    past = history.get_recent(req.session_id, req.user_id, n=10)
    messages = past + [{"role": "user", "content": req.message}]

    if intent_classifier.classify_intent(messages) == "non_domain":
        reply = direct_agent.reply(messages, user)
    else:
        text, tool_results = planner.run(user, req.user_id, messages)
        reply = response_agent.compose(req.message, text, tool_results)

    # save both sides of this exchange (only reached if everything above succeeded)
    history.add_turn(req.session_id, req.user_id, "user", req.message)
    history.add_turn(req.session_id, req.user_id, "assistant", reply)

    return ChatResponse(reply=reply)


# Simple chat page served from the same process, so /chat is same-origin (no CORS needed).
app.mount("/ui", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="ui")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/ui/")
