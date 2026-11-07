"""Assign each new message to 'dev' (for tuning and training) or 'test' (frozen, never tuned on).

    python -m ml.split              # about 30% of NEW groups go to test
    python -m ml.split --test-frac 0.3

Rules that protect the test set:
  * A row that already has a split is NEVER changed. Once a message is in test, it stays there.
  * Messages with the same 'group' stay together. Put near-copies (the same scam template, the
    same sender wording) in one group, otherwise a rule or model tuned on one copy "passes" its
    twin in the test set and the numbers look better than they really are.
  * Made-up messages (self_written, synthetic_ai) always go to dev. Only real messages can be in test.
  * New groups are shuffled with a fixed seed and spread over every (language, label) pair,
    so each language gets some test messages.
"""
from __future__ import annotations

import argparse
import random
from collections import Counter, defaultdict

from .data import NEVER_TEST, load_rows, save_rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-frac", type=float, default=0.30)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rows = load_rows()
    for r in rows:
        r["group"] = r["group"] or r["id"]
        if not r["split"] and r["source"] in NEVER_TEST:
            r["split"] = "dev"  # made-up messages are never used to grade the tool

    # Groups that already have a split keep it. A group split across dev and test is a mistake.
    fixed: dict[str, str] = {}
    for r in rows:
        if r["split"]:
            if fixed.setdefault(r["group"], r["split"]) != r["split"]:
                raise SystemExit(f"Group {r['group']!r} is in both dev and test. Fix data/messages.csv.")

    new_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in rows:
        if r["group"] not in fixed and r["group"] not in {g for v in new_groups.values() for g in v}:
            new_groups[(r["lang"], r["label"])].append(r["group"])

    rng = random.Random(args.seed)
    for key in sorted(new_groups):
        groups = sorted(new_groups[key])
        rng.shuffle(groups)
        n_test = round(len(groups) * args.test_frac)
        for i, g in enumerate(groups):
            fixed[g] = "test" if i < n_test else "dev"

    for r in rows:
        r["split"] = fixed[r["group"]]
    save_rows(rows)

    counts = Counter((r["split"], r["lang"], r["label"]) for r in rows)
    print(f"{'lang':9s} {'dev scam':>9s} {'dev ok':>7s} {'test scam':>10s} {'test ok':>8s}")
    for lang in ["en", "hinglish", "hi", "mr", "ml"]:
        print(f"{lang:9s} {counts[('dev', lang, '1')]:9d} {counts[('dev', lang, '0')]:7d} "
              f"{counts[('test', lang, '1')]:10d} {counts[('test', lang, '0')]:8d}")
    print(f"total: {len(rows)} messages, {sum(1 for r in rows if r['split'] == 'test')} in the test set")


if __name__ == "__main__":
    main()
