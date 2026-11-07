"""Stress-test the tool on an outside labelled SMS file (never part of our own dataset).

    python -m ml.external_check data\\external\\SMSSpamCollection

File format: one message per line, "ham<TAB>text" or "spam<TAB>text" (the UCI SMS Spam Collection),
or a .csv file with columns text,label where label is ham or spam.

What this tells you:
  * ham flagged  = false alarms on normal messages written by other people
  * spam flagged = how many of THEIR spam messages we flag. Their spam is mostly UK
    premium-rate offers, not Indian scams, so a low number here is expected and is NOT our accuracy.

Keep outside datasets in data/external/ (git-ignored). Do not commit them to GitHub.
"""
import sys

from app.analyzer import analyze

from .data import wilson

THRESHOLD = 30


def main(path: str) -> None:
    rows = []
    if path.lower().endswith(".csv"):
        import csv
        with open(path, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if r.get("label") in ("ham", "spam") and r.get("text"):
                    rows.append((r["label"], r["text"]))
    else:
        with open(path, encoding="latin-1") as f:
            for line in f:
                label, _, text = line.rstrip("\n").partition("\t")
                if label in ("ham", "spam") and text:
                    rows.append((label, text))
    scored = [(label, text, analyze(text)["score"]) for label, text in rows]
    for label in ("ham", "spam"):
        group = [s for s in scored if s[0] == label]
        flagged = [s for s in group if s[2] >= THRESHOLD]
        lo, hi = wilson(len(flagged), len(group))
        print(f"{label}: {len(group)} messages, flagged {len(flagged)} "
              f"({100 * len(flagged) / len(group):.1f}%, 95% range {100 * lo:.1f}-{100 * hi:.1f}%)")
    print("\nNormal messages that were flagged (check each one):")
    seen = set()
    for label, text, score in sorted(scored, key=lambda s: -s[2]):
        if label == "ham" and score >= THRESHOLD and text not in seen:
            seen.add(text)
            print(f"  [{score}] {text[:110]}")


if __name__ == "__main__":
    main(sys.argv[1]) if len(sys.argv) == 2 else print(__doc__)
