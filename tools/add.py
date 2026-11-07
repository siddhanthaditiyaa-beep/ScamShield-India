"""Add scrubbed, reviewed messages to data/messages.csv.

    python -m tools.add data/inbox/scrubbed.csv

Input columns: text,label,lang,source,category[,group]   (see data/inbox/template.csv)
It refuses the whole file if any row is invalid, still has personal details, or repeats a
message already in the dataset. New rows get an id and an empty split. Then run: python -m ml.split
"""
import csv
import sys

from ml.data import LANGS, SOURCES, load_rows, save_rows
from tools.scrub import leftovers


def main(path: str) -> int:
    with open(path, encoding="utf-8", newline="") as f:
        new = list(csv.DictReader(f))
    rows = load_rows()
    seen = {" ".join(r["text"].lower().split()) for r in rows}
    problems = []
    for n, r in enumerate(new, start=2):
        text = (r.get("text") or "").strip()
        key = " ".join(text.lower().split())
        if not text:
            problems.append(f"line {n}: empty text")
        if r.get("label") not in {"0", "1"}:
            problems.append(f"line {n}: label must be 0 or 1")
        if r.get("lang") not in LANGS:
            problems.append(f"line {n}: lang must be one of {sorted(LANGS)}")
        if r.get("source") not in SOURCES:
            problems.append(f"line {n}: source must be one of {sorted(SOURCES)}")
        if leftovers(text):
            problems.append(f"line {n}: personal details left ({', '.join(leftovers(text))})")
        if key in seen:
            problems.append(f"line {n}: duplicate message")
        seen.add(key)
    if problems:
        print("\n".join(problems))
        print("Nothing was added. Fix the file and run again.")
        return 1
    start = len(rows)
    for i, r in enumerate(new, start=1):
        rid = f"m{start + i:04d}"
        rows.append({"id": rid, "text": r["text"].strip(), "label": r["label"], "lang": r["lang"],
                     "source": r["source"], "category": r.get("category") or "other",
                     "group": r.get("group") or rid, "split": ""})
    save_rows(rows)
    print(f"Added {len(new)} messages. Total {len(rows)}. Now run: python -m ml.split")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]) if len(sys.argv) == 2 else print(__doc__) or 2)
