# ScamShield India

Paste an SMS or WhatsApp message and find out if it looks like a scam, **and why**, in plain words.
Built for the scams that hit India hardest: fake KYC alerts, UPI PIN tricks, digital arrest threats,
fake parcel and customs fees, fake loans, job offers and fake refunds. Works with English, Hinglish,
Hindi, Marathi and Malayalam.

> **Status: early prototype.** The tool runs and has tests, but it has **not yet been measured on real
> scam messages**. See [What has been measured](#what-has-been-measured). It is a helper, not a guarantee.

<!-- TODO: add a screenshot here: docs/screenshot.png -->

## Why this exists

Most people who fall for these scams are not technical, and most scam checkers only understand English
and give a verdict without a reason. ScamShield explains each warning sign, so people learn to spot the
next scam themselves.

## Example

Made-up message: `Dear customer, your SBI account will be blocked today. Update KYC now: http://sbi-kyc-update.xyz/login`

Result: **95 / 100, likely scam**, because:

- The link imitates a known brand (sbi) but is not on its real website
- It threatens to block your account or asks for a KYC update
- The link ends in a cheap, unusual domain (`.xyz`)
- The link has many hyphens
- Pressure plus a link is the core pattern of phishing

It then tells the user what to do: do not click, never share an OTP, call 1930 (National Cyber Crime
Helpline) if money was lost, and report at cybercrime.gov.in.

## How it works

1. **Rule engine** (`app/rules.py`): explainable checks for OTP requests, look-alike bank links, arrest
   threats, fake refunds, shortened links and more. Each has a weight and a plain-language reason.
   Hindi, Marathi, Malayalam and Hinglish have their own word lists.
2. **Optional ML layer** (`app/ml.py`, `ml/train.py`): TF-IDF text features and logistic regression. It can
   only **raise** a score, and only when it is very confident, so it can never hide a scam the rules found.
   It is not trained yet, because there is not enough real data.
3. **Result** (`app/analyzer.py`): a 0 to 100 score, the reasons, the links found, and advice.
   60 and above = likely scam, 30 to 59 = suspicious, below 30 = "no strong signals" (never "safe").

Messages are analysed in memory and are never stored.

## Run it

In a terminal, inside the project folder (Windows PowerShell):

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. On Mac or Linux, activate with `source .venv/bin/activate`.

Run the tests: `python -m pytest -q`

API: `POST /api/analyze` with `{"message": "..."}` returns the score, label, signals, links and advice.

## What has been measured

No result here is real accuracy yet. This is everything measured so far, and what each number means:

| Check | Result | What it means |
|---|---|---|
| Dev set (131 messages: 41 hand-written seed messages + 90 drafted by an AI) | 100% precision and recall | **Not accuracy.** The rules were tuned on these messages. |
| 18 freshly written scams, before the regional rules were extended | 7 of 18 flagged (39%) | Showed the first regional rules depended on exact wording and spelling. Fixed afterwards, so this check is now used up. |
| 12 freshly written genuine messages | 12 of 12 passed | Small and made up. |
| 4,827 normal English messages (UCI SMS Spam Collection) | 4 flagged (0.1%, 95% range 0.0 to 0.2%) | False-alarm check on casual chat, not on bank alerts. |

The test set for real messages is empty, because no real scam messages have been collected yet.
Made-up messages are never used for testing. Details are in `data/COLLECTION_PLAN.md`.

## Limitations

- **No real-data accuracy yet.** The numbers above come from made-up or non-Indian data.
- Rules are keyword lists. They miss spelling variants and wording they do not list. A first quick check
  showed this clearly for Hindi, Marathi and Malayalam.
- Genuine bank, electricity and KYC reminders can look like scams. They score close to the "suspicious"
  line (25 to 30 out of 100), and some real promotions with short links score 40.
- A sentence containing a word like "not" or "never" is skipped by some rules, so a scam sentence
  containing one can slip through.
- Scam wording changes constantly, so the rules need regular updates.
- The brand allow-list in `app/rules.py` has not been verified.

## Roadmap

- [ ] Collect and label real messages (with permission, personal details removed) and keep a real test set
- [ ] Measure precision and recall on that test set and report the numbers here
- [ ] Review and extend the Hindi, Marathi and Malayalam rules with real examples
- [ ] Train and evaluate the ML layer on real data
- [ ] Handle screenshots (OCR) so people can upload a picture of the message
- [ ] Telegram bot
- [ ] Deploy a live demo

## Project structure

```
app/        FastAPI app, rule engine, ML layer, analyzer
static/     Web interface
data/       Dataset (messages.csv) and the collection plan
ml/         Training, dev/test split, evaluation and stress-test scripts
tools/      Personal-detail scrubber and dataset helper
tests/      Unit and data tests
```

## Data and privacy

- Personal details (names, phone numbers, account numbers, OTPs) are removed before a message is saved.
- Only messages given with permission, or public datasets with a suitable licence, are used.
- Made-up messages (`self_written`, `synthetic_ai`) are labelled and never used for testing.
- Stress tests use the UCI SMS Spam Collection (Almeida, Gomez Hidalgo and Yamakami, 2011; CC BY 4.0).
  It is English, mostly UK and Singapore messages, and is not included in this repository.

## Author

[Siddhanthaditiyaa Vettakal](https://github.com/siddhanthaditiyaa-beep) ·
[LinkedIn](https://www.linkedin.com/in/siddhanthaditiyaa-vettakal)
