"""Optional machine-learning layer. If models/clf.joblib exists it is used next to the rules."""
from __future__ import annotations

from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "clf.joblib"
_model = None
_tried = False


def _load():
    global _model, _tried
    if _tried:
        return _model
    _tried = True
    if MODEL_PATH.exists():
        import joblib
        _model = joblib.load(MODEL_PATH)
    return _model


def scam_probability(text: str) -> float | None:
    """Return P(scam) from the trained model, or None when no model is trained yet."""
    model = _load()
    if model is None:
        return None
    return float(model.predict_proba([text])[0][1])
