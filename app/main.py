"""Run:  uvicorn app.main:app --reload   then open http://127.0.0.1:8000"""
import os
import secrets
from pathlib import Path
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .analyzer import analyze
from .feedback import FeedbackStore
from .ratelimit import RateLimiter

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="ScamShield India", version="0.1.0")


class Message(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class Feedback(BaseModel):
    score: int = Field(..., ge=0, le=100)
    label: Literal["likely_scam", "suspicious", "no_strong_signals"]
    user_label: Literal["scam", "genuine", "unsure"]
    message: Optional[str] = Field(None, max_length=2000)
    consent: bool = False


limiter = RateLimiter()
store = FeedbackStore(Path(os.environ.get("FEEDBACK_PATH", ROOT / "data" / "feedback.jsonl")))


def check_rate(request: Request) -> None:
    """Behind Render's proxy the visitor's address is the first X-Forwarded-For entry."""
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    ip = forwarded or (request.client.host if request.client else "unknown")
    if not limiter.allow(ip):
        raise HTTPException(status_code=429, detail="Too many checks too quickly. Please wait a minute.")


@app.post("/api/analyze", dependencies=[Depends(check_rate)])
def analyze_message(body: Message):
    # The message is analysed in memory and never stored or logged.
    return analyze(body.message)


@app.post("/api/feedback", dependencies=[Depends(check_rate)])
def send_feedback(body: Feedback):
    # Text is stored only when consent is true. See app/feedback.py.
    return store.add(shown_score=body.score, shown_label=body.label, user_label=body.user_label,
                     message=body.message, consent=body.consent)


@app.get("/api/feedback/export")
def export_feedback(token: str = ""):
    """Owner only. Needs the FEEDBACK_TOKEN environment variable; without it this does not exist."""
    wanted = os.environ.get("FEEDBACK_TOKEN", "")
    if not wanted or not secrets.compare_digest(token, wanted):
        raise HTTPException(status_code=404)
    return PlainTextResponse(store.export())


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")
