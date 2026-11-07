"""Import example messages that an agent or a person collected from public web pages.

    python -m tools.import_web data/inbox/web_examples.csv

Input columns: label,message,source,language,type,date_found  (label S or G, source = page URL)

These messages are quoted from public pages. Many pages show them as examples, not as messages a
person really received, and we could not check each one. So they get source=public_web, which can
tune the rules but is NEVER used in the test set (see ml/data.py NEVER_TEST).

What this script does: turns [PHONE]/[ACCT]/[NAME] placeholders into the scrubbed shapes the rest of
the project uses, drops rows listed in DROP_DOMAINS, drops duplicates, runs the personal-detail
check, and appends the rest to data/messages.csv. Then run: python -m ml.split
"""
import csv
import re
import sys

from ml.data import load_rows, save_rows
from tools.scrub import leftovers, scrub

# Domains where a check found a problem (page unrelated to the message, or a video we cannot read).
DROP_DOMAINS = ("lock.pub", "youtube.com")
LANG = {"hindi": "hi", "marathi": "mr", "malayalam": "ml", "hinglish": "hinglish", "english": "en"}
DEVANAGARI_OR_MAL = re.compile(r"[ऀ-ॿഀ-ൿ]")
CATEGORY = {"bill": "bill", "kyc": "kyc", "police": "digital_arrest", "job": "job", "other": "other"}


def clean(text: str) -> str:
    t = text.strip().rstrip("…").strip()
    t = t.replace("[PHONE]", "9000000000").replace("[ACCT]", "000000000000")
    t = re.sub(r"\b(Dear|Hi|Hello)\s+\[NAME\]", r"\1 Customer", t).replace("[NAME]", "Customer")
    return scrub(t)


def lang_of(row: dict, text: str) -> str:
    lang = LANG.get(row["language"].strip().lower(), "en")
    # "hinglish" means Hindi in English letters. Plain English text is labelled en.
    if lang == "hinglish" and not DEVANAGARI_OR_MAL.search(text):
        hinglish_words = re.search(r"\b(aap|aapka|aapki|hai|nahi|karo|karein|kijiye|abhi|turant)\b", text, re.I)
        return "hinglish" if hinglish_words else "en"
    return lang


def main(path: str) -> int:
    with open(path, encoding="utf-8-sig", newline="") as f:
        new = list(csv.DictReader(f))
    rows = load_rows()
    seen = {" ".join(r["text"].lower().split()) for r in rows}
    start, added, dropped, problems = len(rows), 0, [], []
    for n, r in enumerate(new, start=2):
        url = r["source"].strip()
        if any(d in url for d in DROP_DOMAINS):
            dropped.append(f"line {n}: dropped (unverifiable source) {url}")
            continue
        text = clean(r["message"])
        key = " ".join(text.lower().split())
        if key in seen:
            dropped.append(f"line {n}: dropped (duplicate)")
            continue
        if r["label"].strip().upper() not in {"S", "G"}:
            dropped.append(f"line {n}: dropped (label not S or G)")
            continue
        if leftovers(text):
            problems.append(f"line {n}: personal details left ({', '.join(leftovers(text))})")
            continue
        seen.add(key)
        added += 1
        rid = f"w{added:04d}"
        label = "1" if r["label"].strip().upper() == "S" else "0"
        cat = CATEGORY.get(r["type"].strip().lower(), "other") if label == "1" else "other"
        group = "web_electricity" if cat == "bill" and label == "1" else rid
        rows.append({"id": rid, "text": text, "label": label, "lang": lang_of(r, text),
                     "source": "public_web", "category": cat, "group": group, "split": ""})
    print("\n".join(dropped + problems))
    if problems:
        print("Nothing was added. Fix the file and run again.")
        return 1
    save_rows(rows)
    print(f"Added {added} messages ({len(rows) - start}). Total {len(rows)}. Now run: python -m ml.split")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]) if len(sys.argv) == 2 else print(__doc__) or 2)
