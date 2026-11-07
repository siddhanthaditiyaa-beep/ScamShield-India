from app.ratelimit import RateLimiter
from bot.telegram_bot import defang, format_reply, reply_for
from app.analyzer import analyze

SCAM = "Dear customer, your SBI account will be blocked today. Update KYC now: http://sbi-kyc-update.xyz/login"


def msg(text="x", chat_type="private", chat_id=1):
    d = {"chat": {"id": chat_id, "type": chat_type}}
    if text is not None:
        d["text"] = text
    return d


def test_defang_makes_link_untappable():
    assert defang("http://a.xyz/login") == "hxxp://a[.]xyz/login"


def test_scam_reply_has_score_reasons_and_no_live_link():
    out = reply_for(msg(SCAM), RateLimiter())
    assert "Likely a scam" in out and "95/100" in out and "1930" in out
    assert "http://" not in out and "sbi-kyc-update.xyz" not in out


def test_genuine_reply_does_not_say_safe():
    out = reply_for(msg("Your parcel will be delivered today between 2 and 5 pm."), RateLimiter())
    assert "does not mean it is safe" in out


def test_start_gives_help_and_groups_are_ignored():
    assert "not a guarantee" in reply_for(msg("/start"), RateLimiter())
    assert reply_for(msg(SCAM, chat_type="group"), RateLimiter()) is None


def test_non_text_and_too_long():
    assert "only read text" in reply_for(msg(None), RateLimiter())
    assert "too long" in reply_for(msg("a" * 2001), RateLimiter())


def test_rate_limit_per_chat():
    lim = RateLimiter(per_ip=1, total=100)
    assert "Likely" in reply_for(msg(SCAM), lim)
    assert "Too many" in reply_for(msg(SCAM), lim)
    assert "Likely" in reply_for(msg(SCAM, chat_id=2), lim)


def test_reply_never_contains_the_original_message():
    out = format_reply(analyze(SCAM))
    assert "Dear customer" not in out
