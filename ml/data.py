"""Shared helpers for reading the dataset and computing honest statistics."""
from __future__ import annotations

import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "messages.csv"
COLUMNS = ["id", "text", "label", "lang", "source", "category", "group", "split"]
LANGS = {"en", "hinglish", "hi", "mr", "ml"}
SOURCES = {"real_consented", "public_dataset", "self_written", "synthetic_ai"}
NEVER_TEST = {"synthetic_ai", "self_written"}  # made-up messages can tune the tool but never grade it
SPLITS = {"dev", "test"}


def load_rows(path: Path = DATA_PATH) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save_rows(rows: list[dict], path: Path = DATA_PATH) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% confidence interval for a proportion (Wilson score).

    With a small test set, 'recall = 90%' can really mean anything from 75% to 97%.
    This interval shows that range, so we never overclaim.
    """
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))
