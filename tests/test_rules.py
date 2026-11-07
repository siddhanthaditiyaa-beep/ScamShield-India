import pytest

from app.analyzer import analyze
from ml.data import load_rows

# Regression guard: only the 41 seed messages the rules were tuned on must always pass.
# Bigger data sets will always contain some misses. Measure those with python -m ml.evaluate.
ROWS = [r for r in load_rows() if r["id"].startswith("seed")]


@pytest.mark.parametrize("row", [r for r in ROWS if r["label"] == "1"], ids=lambda r: r["id"])
def test_scams_are_flagged(row):
    assert analyze(row["text"])["score"] >= 30, row["text"]


@pytest.mark.parametrize("row", [r for r in ROWS if r["label"] == "0"], ids=lambda r: r["id"])
def test_genuine_messages_pass(row):
    assert analyze(row["text"])["score"] < 30, row["text"]


def test_classic_phishing_is_high_risk():
    r = analyze("Your SBI account will be blocked today. Update KYC: http://sbi-kyc-update.xyz")
    assert r["label"] == "likely_scam"
    assert {"lookalike", "odd_tld", "kyc_threat"} <= {s["id"] for s in r["signals"]}


def test_official_domain_not_lookalike():
    r = analyze("See https://www.hdfcbank.com for details")
    assert "lookalike" not in {s["id"] for s in r["signals"]}


def test_warning_not_flagged_as_otp_request():
    r = analyze("Never share your OTP with anyone.")
    assert "otp_request" not in {s["id"] for s in r["signals"]}
