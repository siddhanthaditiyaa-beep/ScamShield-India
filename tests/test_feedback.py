import json

from fastapi.testclient import TestClient

from app import main
from app.feedback import FeedbackStore
from app.ratelimit import RateLimiter

SCAM = "Dear customer your KYC is expired. Call 9876543210 now or account blocked."


def rows(path):
    return [json.loads(l) for l in open(path, encoding="utf-8")] if path.exists() else []


def test_no_consent_stores_no_text(tmp_path):
    s = FeedbackStore(tmp_path / "f.jsonl")
    out = s.add(shown_score=80, shown_label="likely_scam", user_label="scam", message=SCAM, consent=False)
    assert out == {"saved": True, "kept_text": False}
    assert rows(tmp_path / "f.jsonl")[0]["text"] is None


def test_consent_scrubs_phone(tmp_path):
    s = FeedbackStore(tmp_path / "f.jsonl")
    out = s.add(shown_score=80, shown_label="likely_scam", user_label="scam", message=SCAM, consent=True)
    assert out["kept_text"]
    assert "9876543210" not in rows(tmp_path / "f.jsonl")[0]["text"]


def test_row_has_only_expected_fields_and_date_only(tmp_path):
    s = FeedbackStore(tmp_path / "f.jsonl")
    s.add(shown_score=5, shown_label="no_strong_signals", user_label="genuine", message=None, consent=False)
    r = rows(tmp_path / "f.jsonl")[0]
    assert set(r) == {"day", "shown_score", "shown_label", "user_label", "text"}
    assert len(r["day"]) == 10


def test_row_cap(tmp_path):
    s = FeedbackStore(tmp_path / "f.jsonl", max_rows=2)
    for _ in range(3):
        out = s.add(shown_score=1, shown_label="suspicious", user_label="unsure", message=None, consent=False)
    assert out["saved"] is False
    assert len(rows(tmp_path / "f.jsonl")) == 2


def client(tmp_path, monkeypatch, **limits):
    monkeypatch.setattr(main, "store", FeedbackStore(tmp_path / "f.jsonl"))
    monkeypatch.setattr(main, "limiter", RateLimiter(**limits) if limits else RateLimiter())
    return TestClient(main.app)


def body(**kw):
    d = {"score": 80, "label": "likely_scam", "user_label": "scam", "message": SCAM, "consent": False}
    d.update(kw)
    return d


def test_endpoint_ignores_message_without_consent(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    assert c.post("/api/feedback", json=body()).json()["kept_text"] is False
    assert rows(tmp_path / "f.jsonl")[0]["text"] is None


def test_endpoint_rejects_bad_values(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    assert c.post("/api/feedback", json=body(user_label="maybe")).status_code == 422
    assert c.post("/api/feedback", json=body(score=500)).status_code == 422
    assert c.post("/api/feedback", json=body(message="x" * 2001)).status_code == 422


def test_endpoint_is_rate_limited(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch, per_ip=1, total=100)
    assert c.post("/api/feedback", json=body()).status_code == 200
    assert c.post("/api/feedback", json=body()).status_code == 429


def test_export_hidden_without_token_env(tmp_path, monkeypatch):
    monkeypatch.delenv("FEEDBACK_TOKEN", raising=False)
    c = client(tmp_path, monkeypatch)
    assert c.get("/api/feedback/export").status_code == 404
    assert c.get("/api/feedback/export?token=").status_code == 404


def test_export_needs_right_token(tmp_path, monkeypatch):
    monkeypatch.setenv("FEEDBACK_TOKEN", "s3cret-token")
    c = client(tmp_path, monkeypatch)
    c.post("/api/feedback", json=body(consent=True))
    assert c.get("/api/feedback/export?token=wrong").status_code == 404
    r = c.get("/api/feedback/export?token=s3cret-token")
    assert r.status_code == 200 and "9876543210" not in r.text and "likely_scam" in r.text


def test_import_feedback_skips_unsure_and_blank(tmp_path, monkeypatch):
    from tools import import_feedback as imp
    saved = {}
    monkeypatch.setattr(imp, "load_rows", lambda: [])
    monkeypatch.setattr(imp, "save_rows", lambda r: saved.setdefault("rows", r))
    p = tmp_path / "fb.jsonl"
    lines = [{"text": "Win a free prize, send fee now", "user_label": "scam"},
             {"text": "Your OTP is 123456", "user_label": "unsure"},
             {"text": None, "user_label": "genuine"},
             {"text": "Your parcel is out for delivery", "user_label": "genuine"}]
    p.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
    imp.main(str(p))
    got = saved["rows"]
    assert [r["label"] for r in got] == ["1", "0"]
    assert all(r["source"] == "user_feedback" for r in got)
