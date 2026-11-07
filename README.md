# ScamShield India

Paste an SMS or WhatsApp message and find out if it looks like a scam, **and why**. Built for the scams that hit India hardest: fake KYC alerts, UPI PIN tricks, digital arrest threats, fake parcels and job offers. Works with English, Hinglish, Hindi, Marathi and Malayalam.

> Status: early prototype (v0.1). The checker is a helper, not a guarantee.

<!-- TODO: add a screenshot or GIF here: docs/demo.gif -->

## Why this exists

Most people who fall for these scams are not technical, and most scam checkers only understand English. This tool explains each warning sign in plain words, so people learn to spot the next scam themselves.

## How it works

1. **Rule engine** (`app/rules.py`): explainable checks such as OTP requests, look-alike bank links, threats of arrest, fake refunds and shortened links. Each one has a weight and a plain-language reason.
2. **Optional ML layer** (`app/ml.py`, `ml/train.py`): a text classifier trained on labelled messages. It can only raise the score, and only when it is very confident.
3. **Result** (`app/analyzer.py`): a 0 to 100 risk score, the reasons, the links found, and what to do next, including the 1930 helpline and cybercrime.gov.in.

Messages are analysed in memory and are never stored.

## Run it

Run these in a terminal, inside the project folder:

```
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell. On Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

Run the tests:

```
python -m pytest -q
```

Train the optional ML layer (dev data only; see `data/COLLECTION_PLAN.md`):

```
python -m ml.train
```

Measure it (see `data/COLLECTION_PLAN.md` for the full workflow):

```
python -m ml.evaluate --split dev                    # while tuning
python -m ml.evaluate --split test --confirm-test    # final number, use rarely
```

## API

`POST /api/analyze` with `{"message": "..."}` returns the score, label, signals, links and advice.

## Project structure

```
app/        FastAPI app, rule engine, ML layer, analyzer
static/     Web interface
data/       Dataset (messages.csv) and the collection plan
ml/         Training, dev/test split and evaluation scripts
tools/      Personal-detail scrubber and dataset helper
models/     Trained model (git-ignored)
tests/      Unit tests
```

## Results

No measured results yet. The only numbers so far come from 41 hand-written messages the rules were tuned on, so they are not reported here.

## Limitations

- The seed dataset is tiny. Accuracy numbers mean nothing until you test on a separate set of real messages.
- Scam wording changes constantly, so the rules need regular updates.
- The brand allow-list in `app/rules.py` must be checked and extended.
- Hindi, Marathi and Malayalam rules are keyword lists. They miss spelling variants and wording they do not list. On a quick check with 18 freshly written regional and English scams, the first version of these rules flagged only 7. The rules were then extended, so that check no longer counts.
- Some of the data is made up (`synthetic_ai`, `self_written`). It helps find gaps but cannot show real accuracy.

## Roadmap

- [ ] Collect and label 200+ new messages (with permission, personal details removed), 300 if possible
- [ ] Measure precision and recall on a held-out test set and add the numbers here
- [ ] Add more regional-language rules and test messages
- [ ] Handle screenshots (OCR) so people can upload a picture of the message
- [ ] Telegram bot
- [ ] Deploy a live demo and add the link above

## Data credits

- Stress tests use the UCI SMS Spam Collection (Almeida, Gomez Hidalgo, Yamakami, 2011; CC BY 4.0). It is English, mostly UK and Singapore messages, and is not part of the training or test data. The files are not included in this repository.

## Author

[Siddhanthaditiyaa Vettakal](https://github.com/siddhanthaditiyaa-beep) · [LinkedIn](https://www.linkedin.com/in/siddhanthaditiyaa-vettakal)
