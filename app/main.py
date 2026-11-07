"""Run:  uvicorn app.main:app --reload   then open http://127.0.0.1:8000"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .analyzer import analyze

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="ScamShield India", version="0.1.0")


class Message(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


@app.post("/api/analyze")
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
