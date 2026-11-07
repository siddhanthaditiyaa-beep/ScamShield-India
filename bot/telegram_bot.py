"""Telegram bot for ScamShield India.  Send or forward a message to it and it replies with a risk
score, the reasons and what to do. It uses exactly the same checker as the website.

Run (PowerShell, inside the project folder, after making a token with @BotFather):
    $env:TELEGRAM_BOT_TOKEN = "paste-your-token-here"
    python -m bot.telegram_bot

How it works: "long polling". The bot asks Telegram "any new messages?" in a loop. No web address
and no open port is needed, so it can run on your own computer.

What it does NOT do (on purpose):
  * It only ever replies with a check result. It cannot send, forward or generate scam messages.
  * It does not store messages or log their text. Only the checker runs on them, in memory.
  * It does not repeat the message back, and it shows links defanged (hxxp, [.]) so Telegram does
    not turn them into clickable links.
  * It only answers private chats, not groups.
Honest limits: it is as good as the rules (see the README). Screenshots are not supported here yet.
The token is a password: never put it in the code, in git, or in a screenshot.
"""
from __future__ import annotations

import os
import sys
import time

import httpx

from app.analyzer import analyze
from app.ratelimit import RateLimiter

MAX_CHARS = 2000
LABELS = {"likely_scam": "Likely a scam", "suspicious": "Suspicious",
          "no_strong_signals": "No strong scam signals (this does not mean it is safe)"}

HELP = ("Send or forward me an SMS or WhatsApp message and I will check it for scam signs and explain why. "
        "I work with English, Hinglish, Hindi, Marathi and Malayalam.\n\n"
        "I am a helper, not a guarantee. I do not save your messages. "
        "If you lost money, call 1930 (National Cyber Crime Helpline) and report at cybercrime.gov.in.")


def defang(url: str) -> str:
    """Make a link harmless to look at: it cannot be tapped."""
    return url.replace("http", "hxxp", 1).replace(".", "[.]")


def format_reply(result: dict) -> str:
    lines = [f"{LABELS[result['label']]}  (risk {result['score']}/100)", ""]
    shown = [s for s in result["signals"] if s["weight"] > 0][:5]
    if shown:
        lines.append("Why:")
        lines += [f"- {s['label']}" for s in shown]
        lines.append("")
    if result["urls"]:
        lines.append("Links found (do not open):")
        lines += [f"- {defang(u)}" for u in result["urls"][:3]]
        lines.append("")
    lines.append("What to do:")
    lines += [f"- {a}" for a in result["advice"]]
    return "\n".join(lines)


def reply_for(message: dict, limiter: RateLimiter) -> str | None:
    """Decide the reply for one Telegram message, or None to stay silent."""
    if message.get("chat", {}).get("type") != "private":
        return None
    text = message.get("text")
    if text is None:
        return "I can only read text for now. Please copy the message text and send that."
    if text.strip() in {"/start", "/help"}:
        return HELP
    if not limiter.allow(str(message["chat"]["id"])):
        return "Too many checks too quickly. Please wait a minute and try again."
    if len(text) > MAX_CHARS:
        return f"That message is too long (over {MAX_CHARS} characters). Please send just the suspicious part."
    if not text.strip():
        return None
    return format_reply(analyze(text))


def run(token: str) -> None:
    base = f"https://api.telegram.org/bot{token}"
    limiter = RateLimiter(per_ip=10, total=100)
    offset = None
    print("ScamShield bot is running. Press Ctrl+C to stop.")
    with httpx.Client(timeout=40) as http:
        while True:
            try:
                r = http.get(f"{base}/getUpdates", params={"timeout": 30, "offset": offset,
                                                           "allowed_updates": '["message"]'})
                r.raise_for_status()
                for upd in r.json().get("result", []):
                    offset = upd["update_id"] + 1
                    msg = upd.get("message")
                    reply = reply_for(msg, limiter) if msg else None
                    if reply:
                        http.post(f"{base}/sendMessage", json={"chat_id": msg["chat"]["id"], "text": reply,
                                                               "disable_web_page_preview": True})
            except KeyboardInterrupt:
                print("Stopped.")
                return
            except Exception as e:  # never print e: httpx errors contain the URL, which contains the token
                print(f"Problem talking to Telegram ({type(e).__name__}). Retrying in 5 seconds.")
                time.sleep(5)


if __name__ == "__main__":
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not tok:
        sys.exit("Set TELEGRAM_BOT_TOKEN first. See the top of bot/telegram_bot.py.")
    run(tok)
