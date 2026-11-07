"""Run:  uvicorn app.main:app --reload   then open http://127.0.0.1:8000"""
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .analyzer import analyze
from .ratelimit import RateLimiter

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="ScamShield India", version="0.1.0")


class Message(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


limiter = RateLimiter()


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


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")
