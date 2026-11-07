# Data collection and labelling plan (Step 1)

Goal: at least **200 new messages** (on top of the 41 seed messages), with a frozen test set, so
precision and recall mean something. Stretch goal: 300.

## Targets

| | Minimum | Stretch |
|---|---|---|
| New messages | 200 | 300 |
| Per language (en, hinglish, hi, mr, ml) | 40 | 60 |
| Per language, scam / genuine | 16 / 24 | 24 / 36 |

Why more genuine than scam: a real inbox is mostly genuine messages. Precision depends on that mix.
A 50/50 test set makes precision look better than it would be in daily use. The README must say what
mix the numbers came from.

Why the language targets matter: the seed set has 15 English scams but only 1 scam each in Hindi,
Marathi and Malayalam. After the 70/30 split a language with 40 messages has about 12 in test, so the
per-language numbers will have wide error bars. That is expected. Report them with the intervals the
evaluation script prints, and do not hide them.

## Sources, in order of value

1. **`real_consented`**: real scam and genuine messages that friends and family give you.
   Ask first. Message to send: "I'm building a scam checker for a college project. May I copy the
   text of scam SMS/WhatsApp messages you received, and a few normal ones (bank alerts, delivery,
   OTP)? I will remove names, numbers and account details, and I will not keep the original."
   Copy the text only. No sender numbers, no screenshots saved, nothing from group chats.
2. **`public_dataset`**: only datasets whose licence allows reuse. The UCI SMS Spam Collection is
   English and not specific to India, so use it only for extra English genuine/spam examples, and
   check its licence on the page first. I have not verified any Indian-language scam dataset, so do
   not assume one exists. Record the dataset name and licence in this folder if you use one.
3. **`self_written`**: you write messages from patterns you have seen. Allowed, but labelled as such.
   The rules were tuned by the person who wrote these messages, so they are easier than real ones.
   The evaluation script reports each source separately. Do not let self-written messages
   make up most of a language's test set.

4. **`synthetic_ai`**: messages drafted by Claude from known scam patterns, because real scams can be
   hard to find. You review the Hindi, Marathi and Malayalam ones and fix wording. They always go to
   dev and never to test, and their numbers are reported separately. They help find gaps in the rules.
   They cannot show real accuracy.

Real regional-language scams will be the hardest to get. If you only get 5 real Malayalam scams,
say so in the README. Do not pad the number with self-written ones and call it real.

## What counts as genuine (label 0)

Include hard cases, or the tool will flag everything with a link or the word "urgent":
bank debit/credit alerts, OTPs (with and without "never share"), delivery updates, bill reminders,
real KYC reminders that tell you to visit a branch, telecom plan alerts, IRCTC and ticket messages,
genuine offers with links from known brands, and normal personal and college messages in all five
languages. Genuine marketing is label 0. It is annoying, but it is not fraud.

## Labelling rules (write down any case you were unsure about)

- **1 (scam)**: the message tries to get money, an OTP/PIN/CVV, card or bank details, an app
  install, or control of the device by deception or threat.
- **0 (genuine)**: everything else, including real marketing and warnings about scams.
- If you cannot decide, do not guess. Leave the message out, or ask someone. Ambiguous labels poison both
  training and the test.
- Ask one friend to label 30 mixed messages without seeing your labels. Count disagreements. That
  tells you how clear the labels are.

`category` for scams: kyc, otp, upi, digital_arrest, parcel, loan, refund, lottery, job, bill,
order_alert, remote_access, apk, other. For genuine: otp, bank_alert, delivery, bill, personal, other.
`group`: give near-copies (same scam template, same sender style) the same group name. Leave blank otherwise.

## Workflow (run in Windows PowerShell, in the project folder)

1. Copy `data/inbox/template.csv` to `data/inbox/raw.csv` and add your messages. The `inbox`
   folder is git-ignored, so raw text is never committed.
2. Remove personal details automatically:
   `python -m tools.scrub data\inbox\raw.csv data\inbox\scrubbed.csv`
3. Open `scrubbed.csv` in VS Code and read **every** message. The script does not find names or
   addresses. Fix anything it missed.
4. Add them to the dataset: `python -m tools.add data\inbox\scrubbed.csv`
   (it refuses the file if there are bad values, leftover personal details or duplicates)
5. Assign dev/test: `python -m ml.split`
   Rows already assigned never move, so the test set stays frozen as you add more.
6. Delete `data\inbox\raw.csv` and the original messages.
7. Check: `python -m pytest -q`

## Measuring (the rules that keep the numbers honest)

- Tune rules and train the ML model on **dev only**. Look at mistakes with
  `python -m ml.evaluate --split dev`.
- The test set is for the final number: `python -m ml.evaluate --split test --confirm-test`.
  It prints totals only, never the individual mistakes, and logs every run to `results/test_runs.csv`.
- If you read test mistakes and then change rules, those messages become dev. Collect new test
  messages instead.
- When you add new data later, new messages are split fresh. Old test messages stay test.
- Put in the README: the dataset size and mix, the date, the threshold (30 or 60), and the interval
  next to every number.

## Rough schedule (6 Nov to 6 Dec)

- Week 1: ask for consent, collect the first 100 messages, scrub and add.
- Week 2: reach 200+, split, run the first dev evaluation, list the biggest gaps per language.
- Week 3: improve rules and regional wording using dev only; train the ML layer.
- Week 4: one final test run, update the README with real numbers and limitations, deploy a demo.
