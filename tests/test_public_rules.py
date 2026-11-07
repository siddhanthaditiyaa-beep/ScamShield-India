"""Regression guards for the rules added after testing on public data.

All messages below are written by us (made up), so they only guard against breaking these
rules. They do not measure accuracy.
"""
import pytest

from app.analyzer import analyze


def score(text: str) -> int:
    res = analyze(text)
    return res["score"] if isinstance(res, dict) else res.score


@pytest.mark.parametrize("text", [
    "Dear customer you have W0N Rs.5,00,000 cash prize from SHOPK1NG. Call 9812345678 to claim.",
    "Dear V0DAF0NE user, you are a W1NNER of Rs. 2,00,000 prize. Call 9812345678 now",
    "Your Paytm K.Y.C has expired. Complete your KYC today, call customer care 9812345678",
    "Your ATM card has been De-activated. To re-activate contact customer care on 9812345678 now",
    "Order accepted. Message your name and account number to 9812345678 to confirm",
    "KYC done, get Rs 500 cashback, click http://ab12cd.ngrok.io/pay now",
])
def test_scam_wordings_are_flagged(text):
    assert score(text) >= 30, text


@pytest.mark.parametrize("text", [
    "Solve this case: a man was found murdered. His wife called the police. The police questioned everyone.",
    "Your SBI account is debited by Rs 500. For any queries contact customer care 1800123456.",
    "Congratulations on your selection for the interview round. Please report at 10 am.",
    "Win 10 minutes of fame! I won the quiz at college today.",
    "Mom, call me when you reach. I am at gate 1.",
    "Great. So should I send you my account number for the rent?",
])
def test_ordinary_messages_stay_below_the_flag_line(text):
    assert score(text) < 30, text


def test_malayalam_spelling_variants_score_the_same():
    """OCR and some keyboards write the same Malayalam word with invisible joiners or old-style chillus."""
    plain = "നിങ്ങളുടെ ബാങ്ക് അക്കൗണ്ട് ഇന്ന് ബ്ലോക്ക് ചെയ്യും. ഉടൻ കെവൈസി പുതുക്കുക."
    old_chillu = plain.replace("ഉടൻ", "ഉടന്\u200d")  # na + virama + ZWJ
    with_zwnj = plain.replace("ബ്ലോക്ക്", "ബ്ലോക്ക്\u200c")
    assert score(plain) >= 60
    assert score(old_chillu) == score(plain)
    assert score(with_zwnj) == score(plain)


def test_lottery_screenshot_text_is_flagged_as_likely_scam():
    """Text as read from a phone screenshot: wrapped lines and a phone number written with a space."""
    text = (
        "Congratulations!\nYou have won a Lottery of\nRs 25,00,000 (Twenty Five Lakhs Only)\n"
        "from the Government Lucky Draw 2026.\n\nTo claim your prize, contact our officer\n"
        "immediately on WhatsApp:\n+9198765 43210\nClaim your reward within 24 hours,\n"
        "otherwise it will be cancelled."
    )
    assert score(text) >= 60


def test_sentence_wrapped_by_the_screen_is_still_one_sentence():
    assert score("Hello, please share your\nOTP with our agent to get your refund.") >= 30


def test_support_number_with_a_space_alone_is_not_flagged():
    assert score("Your order has shipped. Contact us on WhatsApp +91 98765 43210 if you need help.") < 30
    assert score("For support call 98765 43210 between 10 am and 6 pm.") < 30
