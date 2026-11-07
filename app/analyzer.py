"""Combines the rule engine and the optional ML model into one explainable result."""
from __future__ import annotations

import re
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


PROMO_CAP = 25
WEAK_ONLY = {"urgency", "short_link", "link_plus_pressure", "refund_details"}
PROMO_WORDS = re.compile(
    r"\b(t\s?&\s?cs?\s+apply|tncs?\s+apply|t&c|terms (and|&) conditions|use code|promo code|coupon|"
    r"\d+\s?%\s?off|rs\.?\s?\d+\s?off|buy \d+ get \d+|b\d+g\d+|stop to \d+|unsubscribe|opt[- ]?out)\b", re.I)


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

    threat = {"ml_bill", "bill_disconnect", "ml_account_threat", "kyc_threat", "ml_kyc", "ml_authority", "ml_parcel"}
    call = {"callback_number", "ml_callback"}
    if ids & threat and ids & call:
        signals.append(rules.Signal("threat_plus_call", "Threat plus 'call this number'", 15,
                                    "A scare message that tells you to call a number is how scammers get you on the phone to pay or share details."))

    rule_score = min(100, sum(s.weight for s in signals))

    # Ordinary store and telecom promotions often have a short link and words like "hurry".
    # If the only things we saw are those weak signals, and the text has clear promotion wording,
    # keep it below the "suspicious" line. Any stronger signal (prize, OTP, KYC, look-alike link,
    # phone number, ...) switches this off. Honest limit: a scam dressed as a promotion with only
    # a short link and "hurry" would also stay low.
    ids = {s.id for s in signals}
    if PROMO_WORDS.search(text) and not (ids - WEAK_ONLY) and rule_score > PROMO_CAP:
        rule_score = PROMO_CAP
        signals.append(rules.Signal("promo_like", "Looks like a store or telecom promotion", 0,
                                    "Ordinary offers use short links and words like 'hurry'. Score was kept low because nothing else looked risky. Still check the sender."))
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
