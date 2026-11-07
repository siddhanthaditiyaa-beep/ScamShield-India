"""Optional "Was this right?" feedback.

Privacy rules (kept simple on purpose):
  * Nothing is stored unless the visitor presses one of the feedback buttons.
  * The message text is stored ONLY if the visitor ticks the consent box. Without it we keep just
    the score shown, the label shown and the visitor's answer (scam / genuine / not sure).
  * Text is cleaned with tools.scrub first (phone, account, card, Aadhaar, PAN, email, UPI id, OTP).
    Names are NOT reliably removed, so the page asks visitors to remove names themselves.
    If anything personal is still visible after cleaning, the text is dropped.
  * No IP address, no user agent, no exact time (only the date) is stored.
Honest limits: on Render's free tier the disk is wiped on every restart or deploy, so feedback can
be lost. Anyone can send feedback, so labels are unverified and can be wrong or deliberate junk.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from tools.scrub import leftovers, scrub

MAX_ROWS = 2000


class FeedbackStore:
    def __init__(self, path: Path, max_rows: int = MAX_ROWS):
        self.path, self.max_rows = Path(path), max_rows
        self._lock = threading.Lock()

    def _count(self) -> int:
        try:
            with open(self.path, encoding="utf-8") as f:
                return sum(1 for _ in f)
        except FileNotFoundError:
            return 0

    def add(self, *, shown_score: int, shown_label: str, user_label: str,
            message: str | None, consent: bool) -> dict:
        text = None
        if consent and message:
            cleaned = scrub(message.strip())[:2000]
            text = cleaned if cleaned and not leftovers(cleaned) else None
        row = {"day": time.strftime("%Y-%m-%d", time.gmtime()), "shown_score": shown_score,
               "shown_label": shown_label, "user_label": user_label, "text": text}
        with self._lock:
            if self._count() >= self.max_rows:
                return {"saved": False, "kept_text": False}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return {"saved": True, "kept_text": text is not None}

    def export(self) -> str:
        try:
            return Path(self.path).read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""
