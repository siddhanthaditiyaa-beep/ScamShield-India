"""Regression tests from OCR text of three made-up lottery screenshots.
These are self-written examples used for tuning. They are NOT evidence of accuracy."""
from pathlib import Path
from app.analyzer import analyze

FIX = Path(__file__).parent / "fixtures"


def _score(name):
    return analyze((FIX / name).read_text(encoding="utf-8"))["score"]


def test_hindi_lottery_screenshot_is_likely_scam():
    assert _score("ocr_hindi_lottery.txt") >= 60


def test_marathi_lottery_screenshot_is_likely_scam():
    assert _score("ocr_marathi_lottery.txt") >= 60


def test_genuine_hindi_and_marathi_contact_messages_stay_low():
    for t in ["आपका बिजली बिल जमा हो गया है। किसी सहायता के लिए ग्राहक सेवा से संपर्क करें 1912।",
              "तुमची ऑर्डर पाठवली आहे. अधिक माहितीसाठी WhatsApp वर संपर्क साधा.",
              "आपकी KYC अपडेट हो गई है। धन्यवाद।"]:
        assert analyze(t)["score"] < 30, t
