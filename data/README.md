# Data

`messages.csv` is the single dataset. Columns: `id,text,label,lang,source,category,group,split`.

- `label`: 1 = scam, 0 = genuine
- `lang`: en, hinglish, hi, mr, ml
- `source`: real_consented, public_dataset, self_written
- `split`: dev (tune and train) or test (frozen, never tuned on)

The first 41 rows are the hand-written seed set. They are `self_written` and all `dev`, and the
rules were tuned on them, so they say nothing about real accuracy.

See `COLLECTION_PLAN.md` for how to collect, scrub, label and split messages.

Rules: remove personal details before saving (`python -m tools.scrub`), never scrape or save other
people's private chats, keep genuine messages in the data, and never train or tune on the test split.
