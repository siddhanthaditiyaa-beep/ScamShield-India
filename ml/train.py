"""Train the optional ML layer on the DEV split only.

    python -m ml.train

The test split is never read for training. To see how good the model really is, run
    python -m ml.evaluate --split test --confirm-test
after training.

The report below is a cross-validated estimate on dev (each message is scored by a model
that did not see its group). It is more honest than scoring the training data, but it is
still only a dev number.
"""
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import make_pipeline

from .data import ROOT, load_rows

rows = [r for r in load_rows() if r["split"] == "dev"]
X = [r["text"] for r in rows]
y = [int(r["label"]) for r in rows]
groups = [r["group"] or r["id"] for r in rows]
print(f"Training on {len(rows)} dev messages ({sum(y)} scam / {len(y) - sum(y)} genuine). Test split not used.")

pipe = make_pipeline(
    TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), lowercase=True, sublinear_tf=True),
    LogisticRegression(max_iter=1000, class_weight="balanced"),
)
pred = cross_val_predict(pipe, X, y, cv=GroupKFold(n_splits=5), groups=groups)
print("Cross-validated on dev (groups kept apart):")
print(classification_report(y, pred, target_names=["genuine", "scam"], zero_division=0))

pipe.fit(X, y)
out = ROOT / "models" / "clf.joblib"
out.parent.mkdir(exist_ok=True)
joblib.dump(pipe, out)
print("saved", out)
