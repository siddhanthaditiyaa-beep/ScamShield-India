"""Measure precision and recall of ScamShield on the dev or test split.

    python -m ml.evaluate --split dev          # use this while you tune rules
    python -m ml.evaluate --split test --confirm-test   # the real number. Use rarely.

'Positive' means the tool flagged the message: score >= threshold (default 30 = "suspicious" or worse).
  precision = of the messages flagged, how many really were scams
  recall    = of the real scams, how many were flagged

Honesty features:
  * Every number comes with a 95% confidence interval and the count behind it.
  * Test mode prints only totals, never the individual mistakes. If you read the mistakes and
    then change rules, the test set has become a second dev set and its numbers are inflated.
  * Every test run is appended to results/test_runs.csv so the number of times you looked is visible.
  * Results are split by language and by source, because self-written messages are easier
    than real ones and must not hide a weak result.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
from collections import defaultdict

from app import ml
from app.analyzer import analyze

from .data import ROOT, load_rows, wilson

RESULTS = ROOT / "results" / "test_runs.csv"


def score_all(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        res = analyze(r["text"])
        out.append({**r, "rules": res["engines"]["rules"], "final": res["score"]})
    return out


def metrics(rows: list[dict], key: str, threshold: int) -> dict:
    tp = sum(1 for r in rows if r["label"] == "1" and r[key] >= threshold)
    fn = sum(1 for r in rows if r["label"] == "1" and r[key] < threshold)
    fp = sum(1 for r in rows if r["label"] == "0" and r[key] >= threshold)
    tn = sum(1 for r in rows if r["label"] == "0" and r[key] < threshold)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def pct(successes: int, n: int) -> str:
    if n == 0:
        return "   n/a"
    lo, hi = wilson(successes, n)
    return f"{100 * successes / n:3.0f}% ({100 * lo:.0f}-{100 * hi:.0f}%, n={n})"


def line(label: str, m: dict) -> str:
    return (f"{label:22s} precision {pct(m['tp'], m['tp'] + m['fp']):26s} "
            f"recall {pct(m['tp'], m['tp'] + m['fn']):26s}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], default="dev")
    ap.add_argument("--threshold", type=int, default=30)
    ap.add_argument("--confirm-test", action="store_true")
    args = ap.parse_args()

    if args.split == "test" and not args.confirm_test:
        raise SystemExit("Test set is for final numbers only. If you are sure, add --confirm-test.")

    rows = [r for r in load_rows() if r["split"] == args.split]
    if not rows:
        raise SystemExit(f"No rows in split '{args.split}'. Run: python -m ml.split")
    scored = score_all(rows)
    n_scam = sum(1 for r in rows if r["label"] == "1")
    print(f"Split: {args.split}   messages: {len(rows)} ({n_scam} scam, {len(rows) - n_scam} genuine)   "
          f"flag if score >= {args.threshold}")
    print(f"ML layer loaded: {ml.scam_probability('test') is not None}\n")

    engines = [("rules only", "rules"), ("rules + ML (final)", "final")]
    overall = {}
    for name, key in engines:
        overall[key] = metrics(scored, key, args.threshold)
        m = overall[key]
        print(line(name, m), f"[TP {m['tp']} FP {m['fp']} FN {m['fn']} TN {m['tn']}]")

    for group_name, field in [("language", "lang"), ("source", "source")]:
        print(f"\nBy {group_name} (final score):")
        buckets = defaultdict(list)
        for r in scored:
            buckets[r[field]].append(r)
        for k in sorted(buckets):
            print(" ", line(k, metrics(buckets[k], "final", args.threshold)))

    if args.split == "dev":
        fns = [r for r in scored if r["label"] == "1" and r["final"] < args.threshold]
        fps = [r for r in scored if r["label"] == "0" and r["final"] >= args.threshold]
        print(f"\nMissed scams (false negatives): {len(fns)}")
        for r in fns:
            print(f"  [{r['final']:3d}] ({r['lang']}, {r['category']}) {r['text'][:110]}")
        print(f"\nFalse alarms (false positives): {len(fps)}")
        for r in fps:
            print(f"  [{r['final']:3d}] ({r['lang']}, {r['category']}) {r['text'][:110]}")
        print("\nThese are DEV numbers. You tuned on this data, so they are optimistic.")
    else:
        RESULTS.parent.mkdir(exist_ok=True)
        new = not RESULTS.exists()
        with open(RESULTS, "a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["when_utc", "n", "n_scam", "threshold", "engine", "tp", "fp", "fn", "tn"])
            for name, key in engines:
                m = overall[key]
                w.writerow([dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), len(rows), n_scam,
                            args.threshold, name, m["tp"], m["fp"], m["fn"], m["tn"]])
        runs = sum(1 for _ in open(RESULTS, encoding="utf-8")) - 1
        print(f"\nTest run logged ({runs // 2} test run(s) so far). Individual mistakes are hidden on purpose.")
        print("Note: precision depends on how many genuine messages the test set holds compared with real life.")


if __name__ == "__main__":
    main()
