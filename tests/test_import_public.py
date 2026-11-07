"""Checks for tools/import_public.py using a tiny made-up dataset (no real data needed)."""
import csv

from tools.import_public import group_key, main


def test_import_keeps_ham_and_smishing_drops_spam_and_uci(tmp_path):
    ds, uci, out = tmp_path / "ds.csv", tmp_path / "uci", tmp_path / "out.csv"
    with open(ds, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["LABEL", "TEXT", "URL", "EMAIL", "PHONE"])
        w.writerow(["Smishing", "You won a prize! Call 9812345678 now", "", "", ""])
        w.writerow(["smishing", "You won a prize! Call 9876543210 now", "", "", ""])  # same after scrub
        w.writerow(["ham", "See you at the station at six", "", "", ""])
        w.writerow(["ham", "Already in the UCI file", "", "", ""])
        w.writerow(["spam", "Buy cheap offers today", "", "", ""])
    uci.write_text("ham\tAlready in the UCI file\n", encoding="utf-8")
    assert main(str(ds), str(uci), str(out)) == 0
    rows = list(csv.DictReader(open(out, encoding="utf-8")))
    assert [r["label"] for r in rows] == ["1", "0"]
    assert all(r["source"] == "public_dataset" for r in rows)
    assert "9812345678" not in rows[0]["text"]


def test_group_ignores_numbers():
    assert group_key("Call 1234567 to claim Rs 500") == group_key("Call 7654321 to claim Rs 900")
