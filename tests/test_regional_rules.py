"""Small checks for the Hindi, Marathi, Malayalam and Hinglish rules.

These sentences are NOT in the dataset. They guard two lessons:
  1. The same word can be spelled several ways (केवाईसी / केवायसी, टेलिग्राम / टेलीग्राम).
  2. A calm reminder (visit your branch) must not be flagged like a threat.
They are regression guards, not a measure of accuracy.
"""
import pytest

from app.analyzer import analyze

SCAMS = [
    "तुमचे खाते आज बंद होईल. केवायसी अपडेट करा: http://x-kyc.top",
    "आपका केवाईसी अपडेट नहीं हुआ, खाता बंद हो जाएगा: http://x-kyc.top",
    "आपको 10 लाख की लॉटरी लगी है, फीस जमा करें।",
    "रोज़ ₹3000 कमाएं, टेलीग्राम पर जुड़ें।",
    "रोज़ ₹3000 कमाएं, टेलिग्राम पर जुड़ें।",
    "Aapne lottery jeeti hai, Rs 2000 jama karein.",
]
GENUINE = [
    "प्रिय ग्राहक, तुमचे केवायसी अपडेट करण्यासाठी जवळच्या शाखेला भेट द्या.",
    "आपका केवाईसी अपडेट बाकी है, कृपया नजदीकी शाखा में आएं।",
    "आज रात 10 बजे से सुबह 5 बजे तक बिजली बंद रहेगी।",
    "നാളെ പവർ കട്ട് ഉണ്ടായിരിക്കും, രാവിലെ 9 മുതൽ 1 വരെ.",
    "आजच्या बैठकीत पोलीस पाटील यांनी माहिती दिली.",
]


@pytest.mark.parametrize("text", SCAMS)
def test_regional_scams_flagged(text):
    assert analyze(text)["score"] >= 30, text


@pytest.mark.parametrize("text", GENUINE)
def test_regional_genuine_not_flagged(text):
    assert analyze(text)["score"] < 30, text
