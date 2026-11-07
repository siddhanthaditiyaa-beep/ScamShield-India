"""Remove personal details from messages BEFORE they are saved in the dataset.

Scrub a file of raw messages (CSV with a 'text' column):
    python -m tools.scrub data/inbox/raw.csv data/inbox/scrubbed.csv

Check that a file has no personal details left (used by the tests too):
    python -m tools.scrub --check data/messages.csv

Replacements keep the SHAPE of the data (a phone number stays a 10-digit number) so the
rules still see realistic text. Names cannot be found reliably by a script, so you must
still read every message yourself before it goes into data/messages.csv.
"""
from __future__ import annotations

import csv
import re
import sys

PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
CARD = re.compile(r"(?<!\d)(?:\d{4}[ -]){3}\d{4}(?!\d)")
AADHAAR = re.compile(r"(?<!\d)\d{4}\s\d{4}\s\d{4}(?!\d)")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
UPI_ID = re.compile(r"\b[\w.\-]{2,}@[a-z]{2,}\b", re.I)
PHONE = re.compile(r"(?<!\d)(?:\+?91[-\s]?)?[6-9]\d{4}[-\s]?\d{5}(?!\d)")  # also 98765 43210
LONG_DIGITS = re.compile(r"(?<!\d)\d{9,18}(?!\d)")  # account, card, reference numbers
OTP_WORD = r"(?:otp|code|pin|passcode|ओटीपी|ഒടിപി)"  # English, Hindi/Marathi, Malayalam
OTP_AFTER = re.compile(r"(" + OTP_WORD + r"[^\d\n]{0,25})(\d{4,8})(?!\d)", re.I)
OTP_BEFORE = re.compile(r"(?<!\d)(\d{4,8})(?!\d)(?=[^.\n]{0,25}" + OTP_WORD + ")", re.I)
URL_QUERY = re.compile(r"(https?://[^\s?]+)\?\S*")  # tracking tokens can identify a person
GREETING_NAME = re.compile(r"\b(Dear|Hi|Hello|Mr\.?|Mrs\.?|Ms\.?|Dr\.?)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?")

# Placeholder values. check() accepts these and rejects any other value of the same shape.
FAKE_PHONE, FAKE_PAN, FAKE_EMAIL, FAKE_UPI = "9000000000", "ABCDE1234F", "user@example.com", "user@bank"


def _fake_otp(m: re.Match) -> str:
    return m.group(1) + "12345678"[: len(m.group(2))]


def scrub(text: str) -> str:
    t = PAN.sub(FAKE_PAN, text)
    t = CARD.sub("0000 0000 0000 0000", t)
    t = AADHAAR.sub("0000 0000 0000", t)
    t = EMAIL.sub(FAKE_EMAIL, t)
    t = UPI_ID.sub(lambda m: m.group(0) if m.group(0) == FAKE_EMAIL.split(".")[0] else FAKE_UPI, t)
    t = PHONE.sub(FAKE_PHONE, t)
    t = LONG_DIGITS.sub(lambda m: m.group(0) if m.group(0) == FAKE_PHONE else "0" * len(m.group(0)), t)
    t = OTP_AFTER.sub(_fake_otp, t)
    t = OTP_BEFORE.sub(lambda m: "12345678"[: len(m.group(1))], t)
    t = URL_QUERY.sub(r"\1", t)
    t = GREETING_NAME.sub(lambda m: m.group(1) + " Customer", t)
    return t


def leftovers(text: str) -> list[str]:
    """Return the kinds of personal detail still visible in a text (empty list = clean)."""
    found = []
    if any(m != FAKE_PAN for m in PAN.findall(text)):
        found.append("PAN")
    if any(re.sub(r"\D", "", m) != "0" * 16 for m in CARD.findall(text)):
        found.append("card number")
    if any(set(re.sub(r"\D", "", m)) != {"0"} for m in AADHAAR.findall(text)):
        found.append("Aadhaar-like number")
    if any(m != FAKE_EMAIL for m in EMAIL.findall(text)):
        found.append("email")
    if any(m not in (FAKE_UPI, FAKE_EMAIL) for m in UPI_ID.findall(text) if "." not in m.split("@")[-1]
           and m != "user@example"):
        found.append("UPI id")
    if any(re.sub(r"\D", "", m)[-10:] != FAKE_PHONE for m in PHONE.findall(text)):
        found.append("phone number")
    if any(set(m) != {"0"} and m != FAKE_PHONE for m in LONG_DIGITS.findall(text)):
        found.append("long digit string")
    if any(m.group(2) != "12345678"[: len(m.group(2))] for m in OTP_AFTER.finditer(text)) or \
       any(m.group(1) != "12345678"[: len(m.group(1))] for m in OTP_BEFORE.finditer(text)):
        found.append("OTP value")
    if URL_QUERY.search(text):
        found.append("URL with query string")
    if GREETING_NAME.search(text) and not re.search(r"\b(Dear|Hi|Hello|Mr\.?|Mrs\.?|Ms\.?|Dr\.?)\s+Customer\b", text):
        found.append("name after greeting")
    return found


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "--check":
        with open(argv[1], encoding="utf-8", newline="") as f:
            bad = [(i + 2, leftovers(r["text"])) for i, r in enumerate(csv.DictReader(f))]
        bad = [(line, kinds) for line, kinds in bad if kinds]
        for line, kinds in bad:
            print(f"line {line}: {', '.join(kinds)}")
        print("clean" if not bad else f"{len(bad)} message(s) still contain personal details")
        return 1 if bad else 0
    if len(argv) == 2:
        with open(argv[0], encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows, fields = list(reader), reader.fieldnames
        changed = 0
        for r in rows:
            new = scrub(r["text"])
            changed += new != r["text"]
            r["text"] = new
        with open(argv[1], "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print(f"{len(rows)} messages scrubbed ({changed} changed) -> {argv[1]}")
        print("Now READ every message yourself: names and addresses are not caught by this script.")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
