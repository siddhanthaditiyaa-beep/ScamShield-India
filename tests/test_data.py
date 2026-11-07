"""Guards for the dataset itself: schema, privacy, and a clean split."""
from collections import defaultdict

from ml.data import COLUMNS, DATA_PATH, LANGS, SOURCES, SPLITS, load_rows
from tools.scrub import leftovers, scrub

ROWS = load_rows()


def test_columns_and_values_are_valid():
    assert list(ROWS[0].keys()) == COLUMNS
    for r in ROWS:
        assert r["text"].strip(), r["id"]
        assert r["label"] in {"0", "1"}, r["id"]
        assert r["lang"] in LANGS, r["id"]
        assert r["source"] in SOURCES, r["id"]
        assert r["split"] in SPLITS, f"{r['id']}: run python -m ml.split"


def test_ids_are_unique_and_no_duplicate_texts():
    ids = [r["id"] for r in ROWS]
    texts = [" ".join(r["text"].lower().split()) for r in ROWS]
    assert len(ids) == len(set(ids))
    assert len(texts) == len(set(texts)), "duplicate message text found"


def test_no_group_is_split_between_dev_and_test():
    seen = defaultdict(set)
    for r in ROWS:
        seen[r["group"] or r["id"]].add(r["split"])
    assert all(len(v) == 1 for v in seen.values())


def test_no_personal_details_left_in_dataset():
    bad = {r["id"]: leftovers(r["text"]) for r in ROWS if leftovers(r["text"])}
    assert not bad, f"personal details left in {bad}. Run python -m tools.scrub"


def test_scrub_removes_personal_details():
    raw = ("Dear Rahul Sharma, call 9876543210 or +91 98765 43210. A/c 123456789012, "
           "PAN ABCPD1234E, mail rahul@gmail.com, pay rahul@oksbi. Your OTP is 482913. "
           "Track https://x.com/t?id=77")
    assert leftovers(raw)
    assert leftovers(scrub(raw)) == []


def test_scrub_keeps_normal_text_and_warnings():
    t = "Rs 1,200 debited from A/c XX1234. Never share your OTP with anyone."
    assert scrub(t) == t


def test_scrub_handles_hindi_otp():
    assert "481920" not in scrub("आपका ओटीपी 481920 है।")
