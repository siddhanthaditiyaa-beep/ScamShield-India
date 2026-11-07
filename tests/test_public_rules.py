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
