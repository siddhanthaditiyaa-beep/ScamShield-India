"""Combines the rule engine and the optional ML model into one explainable result."""
from __future__ import annotations

from dataclasses import asdict

from . import ml, rules

LIKELY, SUSPICIOUS = 60, 30
ML_TRUST = 0.80  # the ML layer may only RAISE the score, and only when it is this confident

ADVICE = {
    "likely_scam": [
        "Do not click any link, call any number or reply.",
        "Never share an OTP, UPI PIN, CVV or card details with anyone.",
        "If you already shared details or paid, call your bank at once and dial 1930 (National Cyber Crime Helpline).",
        "Report it at cybercrime.gov.in, then block and delete the message.",
    ],
    "suspicious": [
        "Do not click the link. Open your bank or app yourself instead.",
        "Check with the organisation using the number printed on your card or its official website.",
        "If it asks for money, details or an OTP, treat it as a scam.",
    ],
    "no_strong_signals": [
        "No strong scam signals found, but this check is not a guarantee.",
        "Still avoid sharing OTPs or PINs and avoid links you were not expecting.",
    ],
}


def _label(score: int) -> str:
    if score >= LIKELY:
        return "likely_scam"
    if score >= SUSPICIOUS:
        return "suspicious"
    return "no_strong_signals"


def analyze(message: str) -> dict:
    text = message.strip()
    urls = rules.extract_urls(text)
    signals = rules.text_signals(text) + rules.link_signals(urls)

    ids = {s.id for s in signals}
    pressure = {"urgency", "kyc_threat", "ml_pressure", "ml_account_threat", "ml_kyc", "ml_otp", "otp_request", "bill_disconnect"}
    if urls and ids & pressure:
        signals.append(rules.Signal("link_plus_pressure", "Pressure plus a link", 10,
                                    "A link combined with pressure to act fast is the core pattern of phishing."))

    prize = {"prize_lottery", "ml_lottery"}
    contact = {"callback_number", "ml_callback", "chat_move", "ml_chat_move"}
    if ids & prize and ids & contact:
        signals.append(rules.Signal("prize_plus_contact", "Prize plus 'contact us to claim'", 20,
                                    "A surprise prize that you must claim by calling or messaging a number is the standard lottery scam."))

    rule_score = min(100, sum(s.weight for s in signals))
    ml_prob = ml.scam_probability(text)
    ml_score = round(ml_prob * 100) if ml_prob is not None else None
    score = max(rule_score, ml_score) if ml_prob is not None and ml_prob >= ML_TRUST else rule_score
    label = _label(score)

    return {
        "score": score,
        "label": label,
        "signals": [asdict(s) for s in sorted(signals, key=lambda s: -s.weight)],
        "urls": urls,
        "advice": ADVICE[label],
        "engines": {"rules": rule_score, "ml": ml_score},
    }
