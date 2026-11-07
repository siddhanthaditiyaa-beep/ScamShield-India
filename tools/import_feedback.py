"""Import visitor feedback that you exported from the live site.

    1. Download:  https://YOUR-SITE/api/feedback/export?token=YOUR_FEEDBACK_TOKEN  -> data/inbox/feedback.jsonl
    2. Run:       python -m tools.import_feedback data/inbox/feedback.jsonl
    3. Then:      python -m ml.split

Only rows that have message text AND a clear answer (scam or genuine) are used. "Not sure" rows are skipped.
Rows get source=user_feedback: anyone can send feedback, so the labels are unverified and can be
wrong or deliberate junk. They may tune the rules but are NEVER used in the test set. Look at each new
row yourself before trusting it. Only after you check one by hand may you change its source to
real_consented (and only if the person really agreed, which the tick box records).
"""
import json
import re
import sys

from ml.data import load_rows, save_rows
from tools.scrub import leftovers, scrub

SCRIPT = {"hi": re.compile(r"[ऀ-ॿ]"), "ml": re.compile(r"[ഀ-ൿ]")}


def guess_lang(text: str) -> str:
    if SCRIPT["ml"].search(text):
        return "ml"
    if SCRIPT["hi"].search(text):
        # Hindi and Marathi share a script and we cannot tell them apart safely. Fix by hand if needed.
        return "hi"
    return "en"


def main(path: str) -> int:
    rows = load_rows()
    seen = {" ".join(r["text"].lower().split()) for r in rows}
    last = max([int(r["id"][1:]) for r in rows if re.fullmatch(r"f\d{4}", r["id"])] or [0])
    added = skipped = 0
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            if not line.strip():
                continue
            fb = json.loads(line)
            text = scrub((fb.get("text") or "").strip())
            key = " ".join(text.lower().split())
            if not text or fb.get("user_label") not in {"scam", "genuine"} or key in seen or leftovers(text):
                skipped += 1
                continue
            seen.add(key)
            added += 1
            rid = f"f{last + added:04d}"
            rows.append({"id": rid, "text": text, "label": "1" if fb["user_label"] == "scam" else "0",
                         "lang": guess_lang(text), "source": "user_feedback",
                         "category": "other", "group": rid, "split": ""})
    save_rows(rows)
    print(f"Added {added}, skipped {skipped}. Total {len(rows)}. Now run: python -m ml.split")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]) if len(sys.argv) == 2 else print(__doc__) or 2)
