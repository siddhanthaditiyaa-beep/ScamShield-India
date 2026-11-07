"""Turn the Mendeley "SMS Phishing Dataset" into a file that tools.add accepts.

    python -m tools.import_public data\\external\\Dataset_5971.csv data\\external\\SMSSpamCollection data\\inbox\\mendeley.csv

What it does, and why:
  1. Keeps only 'smishing' (scam, label 1) and 'ham' (genuine, label 0).
     It DROPS 'spam': promotional messages are not scams (our rule: promotions are label 0),
     and the dataset's spam rows are not checked one by one, so we do not guess.
  2. Drops every message that is also in the UCI SMSSpamCollection file. We keep UCI as a
     separate outside check (ml.external_check), so its messages must not enter our data.
  3. Scrubs personal details (same scrubber as everything else).
  4. Gives near-identical messages (same text, only numbers differ) one shared 'group', so the
     split never puts one copy in dev and another in test.
  5. Marks the source as 'public_dataset'. Language is 'en' unless clear Hinglish words appear.

Data: "SMS Phishing Dataset for Machine Learning and Pattern Recognition" (Mendeley Data,
CC BY 4.0). Credit the authors in the README. The raw file stays in data/external (git-ignored).
"""
from __future__ import annotations

import csv
import hashlib
import re
import sys

from ml.data import load_rows
from tools.scrub import leftovers, scrub

HINGLISH = {"hai", "hain", "aap", "kya", "nahi", "kuch", "bhi", "hum", "mein", "tum", "karo",
            "pehle", "zindgi", "naseeb", "bhai", "waqt", "kisi", "mujhe", "tumhe"}


def norm(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def group_key(text: str) -> str:
    """Same wording with different numbers/amounts -> same group."""
    core = re.sub(r"\d+", "", norm(text))
    core = re.sub(r"\s+", " ", core)[:50]
    return "pd_" + hashlib.md5(core.encode()).hexdigest()[:8]


def category(text: str, label: int) -> str:
    if not label:
        return "other"
    t = text.lower()
    if "kyc" in t:
        return "kyc"
    if re.search(r"won|prize|award|lottery|draw|winner", t):
        return "lottery"
    if re.search(r"bank|account|atm|card|apple id|paypal", t):
        return "bank_alert"
    return "other"


def load_uci(path: str) -> set[str]:
    seen = set()
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t", 1)
            if len(parts) == 2:
                seen.add(norm(parts[1]))
    return seen


def main(dataset: str, uci_path: str, out: str) -> int:
    uci = load_uci(uci_path)
    with open(dataset, encoding="utf-8", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f))
    kept, seen, seen_clean = [], set(), set()
    existing = {" ".join(r["text"].lower().split()) for r in load_rows()}
    counts = {"spam_dropped": 0, "in_uci": 0, "duplicate": 0, "duplicate_after_scrub": 0, "empty": 0}
    for r in rows:
        lab = (r.get("LABEL") or "").strip().lower()
        if lab not in {"ham", "smishing"}:
            counts["spam_dropped"] += 1
            continue
        text = " ".join((r.get("TEXT") or "").replace("�", "").split())
        if not text:
            counts["empty"] += 1
            continue
        key = norm(text)
        if key in uci:
            counts["in_uci"] += 1
            continue
        if key in seen:
            counts["duplicate"] += 1
            continue
        seen.add(key)
        label = 1 if lab == "smishing" else 0
        lang = "hinglish" if set(re.findall(r"[a-z]+", text.lower())) & HINGLISH else "en"
        clean = scrub(text)
        # scrubbing can make two different messages identical (only the phone number differed)
        if norm(clean) in seen_clean or " ".join(clean.lower().split()) in existing:
            counts["duplicate_after_scrub"] += 1
            continue
        seen_clean.add(norm(clean))
        kept.append({"text": clean, "label": label, "lang": lang, "source": "public_dataset",
                     "category": category(clean, label), "group": group_key(clean)})
    bad = [k for k in kept if leftovers(k["text"])]
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["text", "label", "lang", "source", "category", "group"])
        w.writeheader()
        w.writerows(kept)
    scam = sum(k["label"] for k in kept)
    groups = len({k["group"] for k in kept})
    print(f"Read {len(rows)} rows. Dropped: {counts}")
    print(f"Wrote {len(kept)} messages to {out}: {scam} scam, {len(kept) - scam} genuine, "
          f"{groups} groups, {sum(k['lang'] == 'hinglish' for k in kept)} Hinglish.")
    if bad:
        print(f"WARNING: {len(bad)} still have personal details; tools.add will refuse them.")
    print("Now: read a sample yourself, then run: python -m tools.add", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]) if len(sys.argv) == 4 else print(__doc__) or 2)
