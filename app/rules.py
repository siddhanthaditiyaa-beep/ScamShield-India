"""Rule engine: small, explainable checks for common Indian scam patterns.

Every signal has an id, a weight and a plain-language reason, so the app can show
WHY a message was flagged. Tune the weights as you test on real messages.
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class Signal:
    id: str
    label: str
    weight: int
    why: str


# --------------------------------------------------------------------------
# Text rules. Each rule is (id, label, weight, why, [regex patterns], sentence_level)
# sentence_level=True skips any sentence that contains a negation such as
# "do not share your OTP", so genuine bank warnings are not flagged.
# --------------------------------------------------------------------------
NEGATION = re.compile(
    r"\b(do not|don't|dont|never|not|mat)\b|मत|न करें|नका|नको|ചെയ്യരുത്", re.I
)

TEXT_RULES = [
    ("otp_request", "Asks you to share an OTP, PIN or CVV", 35,
     "Real banks and apps never ask you to send or tell them an OTP, PIN or CVV.",
     [r"\b(share|send|tell|give|provide|forward|reply with)\b.{0,40}\b(otp|pin|cvv|password|passcode)\b",
      r"\b(otp|pin|cvv)\b.{0,25}\b(share|send|tell|give|batao|bhejo)\b"], True),
    ("upi_collect", "Tricks you into entering your UPI PIN to 'receive' money", 30,
     "You never need your UPI PIN to receive money. Entering it sends money out.",
     [r"\bupi pin\b.{0,40}\b(receive|get|credit|refund|cashback)\b",
      r"\b(receive|get|credit|refund|cashback)\b.{0,40}\bupi pin\b",
      r"\benter (your )?(upi )?pin\b",
      r"\bscan\b.{0,30}\b(qr|code)\b.{0,40}\b(receive|get|refund|cashback)\b",
      r"\bmoney\b.{0,20}\b(sent|transferred)\b.{0,20}\bby mistake\b"], False),
    ("kyc_threat", "Threatens to block your account or asks for a KYC update", 25,
     "Scammers use fake 'KYC pending' or 'account blocked' alerts to push you to a fake link.",
     [r"\bkyc\b.{0,50}\b(update|expire[ds]?|pending|verify|verification|incomplete|suspend|block)",
      r"\bcomplete\b.{0,20}\bkyc\b",
      r"\b(pan|aadhaar|aadhar)\b.{0,40}\b(update|link|not linked|block|suspend|deactivat|verify)",
      r"\b(account|a/c|card|sim|wallet)\b.{0,40}\b(blocked|block|suspend\w*|frozen|freez\w*|de-?activat\w*|disconnect\w*|closed)\b"], False),
    ("urgency", "Creates time pressure", 15,
     "Scams rush you so you act before thinking. Genuine organisations give you time.",
     [r"\b(immediately|urgent(ly)?|right now|asap|tonight|today only|last chance|act now|don'?t ignore)\b",
      r"\b(within|in)\s+\d+\s*(hours?|hrs?|minutes?|mins?)\b",
      r"\bexpires?\s+(today|soon|tonight)\b",
      r"\bfinal\s+(notice|warning|reminder)\b"], False),
    ("prize_lottery", "Claims you won a prize, lottery or reward", 25,
     "You cannot win a contest you never entered. These messages ask for fees or details to 'claim' it.",
     [r"\b(you\s+(have\s+)?won|you('| a)?re selected|lucky draw|lottery|jackpot)\b",
      r"\bcongratulations\b.{0,80}\b(won|prize|reward|gift|cashback|claim)\b",
      r"\bclaim\b.{0,30}\b(prize|reward|gift|cashback)\b",
      r"\byou\s+(are|were|have been|'ve been)\s+(a\s+)?(randomly\s+)?(selected|chosen|picked|awarded|the\s+winner|a\s+winner)\b.{0,60}\b(prize|award|gift|cash|reward|bonus|lakh|crore|rs\b|inr|\u20b9|\u00a3|\$)",
      r"\b(mobile\s+)?(number|no\.?)\s+(has|have)\s+won\b",
      r"\bu\s+(have\s+)?won\b",
      r"\bwinner\b.{0,40}\b(prize|rs\b|inr|lakh|crore|\u20b9)"], False),
    ("job_scam", "Looks like a fake work-from-home or task job offer", 25,
     "Fake job offers promise easy daily income, then ask you to pay or move to Telegram.",
     [r"\bwork from home\b",
      r"\bearn\b.{0,25}\b(per day|daily|a day|/day|per hour|weekly)\b",
      r"\b(part[- ]time|online)\s+job\b",
      r"\bcomplete\b.{0,15}\btasks?\b"], False),
    ("chat_move", "Pushes you to Telegram or WhatsApp", 10,
     "Scammers move you to chat apps where there is no record and no protection.",
     [r"\b(telegram|whatsapp)\b.{0,40}\b(join|group|contact|apply|message us)\b", r"\bt\.me/"], False),
    ("parcel_customs", "Fake parcel or customs fee", 20,
     "Courier and customs scams ask for a small 'release fee' to steal card or UPI details.",
     [r"\b(parcel|courier|package|shipment|consignment)\b.{0,60}\b(held|seized|customs|fee|charges|undelivered|illegal|stuck)\b",
      r"\bcustoms\b.{0,20}\b(duty|fee|clearance|charges)\b"], False),
    ("authority_threat", "Pretends to be police or an agency and threatens arrest", 35,
     "Agencies like CBI, police or customs never arrest people over a call or video call, and never ask for money to close a case.",
     [r"\b(cbi|ncb|narcotics|enforcement directorate|cyber\s?crime|trai|rbi|income tax)\b.{0,80}\b(arrest\w*|warrant|case|fir|illegal|legal action|money laundering|drugs)\b",
      # 'police' and 'customs' are everyday words: only count them when the message is about YOU
      r"\b(you|your)\b.{0,60}\b(police|customs)\b.{0,80}\b(arrest\w*|warrant|case|fir|illegal|legal action|money laundering|drugs)\b",
      r"\b(police|customs)\b.{0,40}\b(you|your)\b.{0,60}\b(arrest\w*|warrant|case|fir|illegal|legal action|money laundering|drugs)\b",
      r"\bdigital arrest\b"], False),
    ("secrecy_demand", "Tells you to keep it secret or stay on the call", 20,
     "Scammers isolate victims. A genuine officer or bank will not forbid you from telling family.",
     [r"\b(do not|don'?t|never)\s+(tell|inform|disclose)\b.{0,20}\b(anyone|family|bank|police)\b",
      r"\bstay on (the )?(video )?call\b", r"\b(do not|don'?t)\s+disconnect\b"], False),
    ("remote_access", "Asks you to install a screen-sharing app", 35,
     "Apps like AnyDesk or TeamViewer give a stranger full control of your phone and bank apps.",
     [r"\b(anydesk|teamviewer|quick\s?support|airdroid|rustdesk|ultraviewer)\b"], False),
    ("apk_install", "Asks you to install an app from a link (APK)", 25,
     "Apps installed outside the Play Store can read your SMS and steal OTPs.",
     [r"\.apk\b", r"\binstall\b.{0,30}\b(this|the|our)\s+(app|apk)\b.{0,40}\b(link|below|click|claim)\b"], False),
    ("bill_disconnect", "Threatens to cut your electricity, SIM or gas", 25,
     "'Your power will be cut tonight' is a common trick to make you call a scam number.",
     [r"\b(electricity|power|gas|water|mobile|sim)\b.{0,40}\b(bill|connection|service|number)\b.{0,60}\b(disconnect\w*|cut|blocked|suspend\w*|tonight|barred)\b",
      r"\b(electricity|power( supply)?|gas)\b.{0,40}\b(will be|shall be|is being)\s+(disconnected|cut)\b.{0,40}\b(today|tonight|tomorrow|\d+\s*(hours?|hrs?))\b"], False),
    ("loan_fee", "Loan approved, but you must pay a fee first", 30,
     "Genuine lenders deduct fees from the loan. Paying a 'processing fee' first is a scam signal.",
     [r"\b(loan|credit limit)\b.{0,50}\b(approved|pre-?approved|sanctioned|instant)\b.{0,80}\b(fee|charges|deposit|advance)\b",
      r"\bprocessing fee\b"], False),
    ("refund_details", "Offers a refund or cashback if you verify bank details", 25,
     "Refund and cashback messages are used to collect your card or bank details.",
     [r"\b(refund|cashback|reward)\b.{0,50}\b(bank (details|account)|card (details|number)|verify|link)\b",
      r"\b(refund|cashback)\b.{0,80}\b(click|tap)\b"], False),
    ("fake_order_alert", "Fake order or payment alert asking you to dispute it", 25,
     "A surprise order confirmation with a number to 'cancel' is a trick to get you on the phone.",
     [r"\b(order|purchase|payment|transaction)\b.{0,60}\b(confirmed|placed|debited)\b.{0,60}\b(if (this|it) (was|is) not you|did not|didn'?t|not placed by you|to cancel)\b"], False),
    ("reward_expiry", "Reward points about to expire", 15,
     "'Your reward points expire today' is a common bait. Check your points in the official app yourself.",
     [r"\b(reward points?|points)\b.{0,60}\b(expire[sd]?|expiring|lapse[sd]?)\b"], False),
    ("callback_number", "Tells you to call a number to cancel or fix something", 15,
     "Scam messages often include a phone number so a fake agent can talk you into paying.",
     [r"\bif (this|it) (was|is) not you\b.{0,40}\bcall\b",
      r"\b(call|contact|whatsapp)\b.{0,30}\b(\+?91[-\s]?)?[6-9]\d{9}\b",
      r"\b(call|contact)\b.{0,25}\bcustomer (care|service)\b"], False),
    ("send_bank_details", "Asks you to send your account or card details", 30,
     "No genuine bank, courier or shop asks you to message your account number, card number or bank details.",
     [r"\b(send|message|share|give|provide|reply with)\b.{0,40}\b(account number|card number|bank details|debit card|atm pin)\b"], True),
    # Hindi, Hinglish, Marathi, Malayalam. Starter lists, extend these yourself.
    ("ml_pressure", "Pressure words in Hindi, Marathi or Malayalam", 15,
     "Words meaning 'immediately' are used to rush you.",
     [r"तुरंत|ताबडतोब|त्वरित|लगेच|ഉടൻ|ഉടനെ|\bturant\b|\bjaldi se\b"], False),
    ("ml_account_threat", "Account-block threat in Hindi, Marathi or Malayalam", 25,
     "Messages saying your account will be blocked or closed are a classic scam opener.",
     [r"ब्लॉक|बंद हो जाएगा|बंद होगा|बंद होईल|ബ്ലോക്ക്|\bblock ho jayega\b|\bband ho jayega\b|\bband ho jaayega\b|\bbandh ho jayega\b"], False),
    ("ml_kyc", "KYC request in Hindi, Hinglish, Marathi or Malayalam", 25,
     "KYC requests by SMS are a classic scam, in any language.",
     [r"केवा[ईय]सी|केवायसी|कायसी|കെവൈസി|കെ\\.?വൈ\\.?സി",
      r"\bkyc\b.{0,30}\b(karo|karein|kijiye|kara)\b"], True),
    ("ml_otp", "Asks for an OTP in Hindi, Marathi or Malayalam", 30,
     "Nobody genuine asks you to share an OTP, in any language.",
     [r"(ओटीपी|ഒടിപി)\W{0,10}(शेयर|शेअर|बताएं|बताओ|बताइए|भेजें|भेजो|പങ്കിടുക|ഷെയർ|അയയ്ക്കുക)",
      r"(शेयर|शेअर|बताएं|बताओ|भेजें)\W{0,10}(ओटीपी)",
      r"\botp\b.{0,20}\b(batao|bhejo|bhejiye|bhejein|bhej do|batayein|batayiye|share karo|dijiye)\b"], True),
    # ---- Regional scam types (Hinglish, Hindi, Marathi, Malayalam). Word lists, not clever tricks.
    # Non-English patterns avoid \\b and \\w because Python treats Indian-script vowel marks as non-letters.
    ("ml_lottery", "Claims you won a lottery or prize (Hindi, Marathi, Malayalam)", 25,
     "You cannot win a contest you never entered. These messages ask for a fee to 'release' the prize.",
     [r"लॉटरी|ലോട്ടറി",
      r"(इनाम|बक्षीस|സമ്മാന).{0,60}(जीत|जिंक|मिल|मिळ|ലഭിക്ക|ലഭിച്ച|അടിച്ച)",
      r"(जीत|जिंक|അടിച്ച).{0,40}(लाख|ലക്ഷം|₹)",
      r"\b(jeet|jeeta|jeete|jeeti|jita|jiti)\w*\b.{0,40}\b(lakh|crore|inaam|inam|prize|lottery)\b"], False),
    ("ml_pay_demand", "Asks you to pay a fee, fine or amount (Hindi, Marathi, Malayalam)", 20,
     "Genuine banks and agencies do not ask for a 'fee' or 'fine' by SMS to release money, a parcel or a case.",
     [r"(शुल्क|जुर्माना|दंड|फीस|ड्युटी|ड्यूटी|चार्ज|പിഴ|ഫീസ്|ചാർജ്).{0,25}(भरें|भरा|भर|जमा|अदा|चुका|അടയ്ക്ക|അയയ്ക്ക)",
      r"(भरें|भरा|जमा करें|जमा करा|അടയ്ക്ക).{0,25}(शुल्क|जुर्माना|दंड|फीस|ड्युटी|ड्यूटी|चार्ज|പിഴ|ഫീസ്|ചാർജ്)",
      r"(₹|rs\.?\s?)\s?\d[\d,]*\s*(रुपये|रुपए|രൂപ)?\W{0,3}(भरा|भरें|जमा|अदा|भेजें|भेजिए|അടയ്ക്ക|അയയ്ക്ക|bhejiye|bhejein|bhejo|jama)",
      r"\d[\d,]*\s*(रुपये|रुपए|രൂപ)\W{0,3}(भरा|भरें|जमा|अदा|भेजें|അടയ്ക്ക|അയയ്ക്ക)"], False),
    ("ml_parcel", "Parcel stopped at customs or caught with something illegal", 20,
     "Courier and customs scams say your parcel is held, then ask for a fee or threaten a case.",
     [r"(पार्सल|पारसल|പാഴ്സൽ).{0,60}(कस्टम|रोका|थांबव|पकड|പിടിച്ച|കസ്റ്റംസ്|ड्रग)",
      r"(कस्टम|കസ്റ്റംസ്).{0,30}(शुल्क|ड्यूटी|जुर्माना|പിഴ|ഫീസ്)"], False),
    ("ml_authority", "Police, customs or agency threat of a case or arrest", 35,
     "Real police and agencies never settle a case or arrest over an SMS or a call. Never pay to close a case.",
     [r"(पुलिस|पोलीस|പോലീസ്|सीबीआई|कस्टम|കസ്റ്റംസ്).{0,80}(केस|गिरफ्तार|अटक|वारंट|वॉरंट|मनी लॉन्ड्रिंग|അറസ്റ്റ്|കേസ്|ड्रग)",
      r"गिरफ्तार|अरेस्ट|അറസ്റ്റ്|\bdigital arrest\b"], False),
    ("ml_secrecy", "Tells you not to tell anyone", 20,
     "Scammers isolate victims. A genuine officer or bank will not forbid you from telling family.",
     [r"(किसी को|कोणालाही|कोणाला|ആരോടും).{0,15}(बताना मत|न बताएं|न बताना|सांगू नका|सांगू नये|പറയരുത്)",
      r"\b(kisi ko|kisi se)\b.{0,20}\b(batana mat|mat batana|mat batao)\b",
      r"(वीडियो कॉल|व्हिडिओ कॉल|വീഡിയോ കോൾ).{0,25}(रहिए|रहें|राहा|पर बने|ഉണ്ടാകണം)",
      r"\bvideo call\b.{0,20}\b(par rahiye|par rahein|par bane rahein)\b"], False),
    ("ml_job", "Fake work-from-home or easy daily income offer", 25,
     "Fake job offers promise easy daily income, then ask you to pay or move to Telegram.",
     [r"(घर बैठे|घरबसल्या|വീട്ടിലിരുന്ന്|ghar baithe).{0,60}(कमा|कमव|സമ്പാദി|earn|kama)",
      r"(कमाएं|कमाएँ|कमवा|സമ്പാദിക്കൂ|\bkamayein\b|\bkamaiye\b)",
      r"(पार्ट[ -]?टाइम|പാർട്ട് ടൈം).{0,40}(जॉब|नौकरी|नोकरी|ജോലി)",
      r"(ദിവസം|दररोज|रोज़?).{0,25}\d{3,6}.{0,25}(വരുമാനം|സമ്പാദ|कमाई|कमा|कमव)"], False),
    ("ml_chat_move", "Pushes you to Telegram or WhatsApp (Hindi, Marathi, Malayalam)", 10,
     "Scammers move you to chat apps where there is no record and no protection.",
     [r"(टेल[िी]ग्राम|ടെലിഗ്രാം).{0,30}(जॉइन|जॉईन|जुड़|ചേര)",
      r"(व्हाट्स[एअ]प|व्हॉट्स[एअ]प|वॉट्स[एअ]प|വാട്സ്ആപ്പ).{0,30}(जुड़|जॉइन|जॉईन|ചേര)",
      r"\bwa\.me/"], False),
    ("ml_upi", "Asks you to enter your UPI PIN (Hindi, Marathi, Malayalam)", 30,
     "You never need your UPI PIN to receive money. Entering it sends money out.",
     [r"(upi|यूपीआई)\s*(पिन|पीन|pin|പിൻ).{0,40}(डाल|दर्ज|एंटर|टाका|नमूद|നൽകു|daal|dalein|enter)",
      r"(डाल|दर्ज|एंटर|टाका|नमूद|നൽകു|daal|dalein).{0,30}(upi|यूपीआई)\s*(पिन|पीन|pin|പിൻ)"], True),
    ("ml_bill", "Threatens to cut your electricity (Hindi, Marathi, Malayalam)", 25,
     "'Your power will be cut tonight' is a common trick to make you call a scam number.",
     [r"(वीज|बिजली|कनेक्शन|കറന്റ്|വൈദ്യുതി|\belectricity\b|\bbijli\b|\bconnection\b).{0,50}(कापले|कट जाएगा|कट जाएगी|कटेगा|काट दिया जाएगा|काटा जाएगा|कनेक्शन कट|വിച്ഛേദ|ഡിസ്കണക്ട്|\bkat jayegi\b|\bkat jaayegi\b|\bkat jayega\b|\bkat jaayega\b)"], False),
    ("ml_callback", "Tells you to call a number (Hindi, Marathi, Malayalam)", 15,
     "Scam messages often include a phone number so a fake agent can talk you into paying.",
     [r"(संपर्क|कॉल|फोन|फ़ोन|विचारपूस|വിളിക്ക|ബന്ധപ്പെട).{0,30}(\+?91[-\s]?)?[6-9]\d{9}"], False),
    ("ml_loan_fee", "Loan approved, but you must pay a fee first", 30,
     "Genuine lenders deduct fees from the loan. Paying a 'file charge' or 'processing fee' first is a scam signal.",
     [r"(लोन|कर्ज|ലോൺ).{0,60}(फीस|शुल्क|चार्ज|ഫീസ്)",
      r"\bloan\b.{0,40}\b(pass|manzoor|sanction)\w*\b.{0,60}\b(charge|fee|bhej|jama|deposit)\w*"], False),
]
_COMPILED = [(i, l, w, why, [re.compile(p, re.I | re.S) for p in pats], sent)
             for (i, l, w, why, pats, sent) in TEXT_RULES]

_SENT_SPLIT = re.compile(r"(?<=[.!?।])\s+|\n")

# --------------------------------------------------------------------------
# Link rules
# --------------------------------------------------------------------------
URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s<>\"')]+"
    r"|\b(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl|cutt\.ly|rb\.gy|is\.gd|shorturl\.at|t\.me|wa\.me)/[^\s<>\"')]+"
    r"|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:xyz|top|click|icu|vip|club|online|site|link|cc|buzz|live|shop|cfd|sbs)\b(?:/[^\s<>\"')]*)?"
    r"|\b[a-z0-9]+(?:-[a-z0-9]+)+\.(?:com|in|net|org|co\.in)\b(?:/[^\s<>\"')]*)?",
    re.I,
)
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "cutt.ly", "rb.gy", "is.gd", "shorturl.at"}
SUSPICIOUS_TLDS = {"xyz", "top", "click", "icu", "vip", "club", "online", "site", "link",
                   "cc", "buzz", "live", "shop", "cfd", "sbs"}
TUNNEL_HOSTS = ("ngrok.io", "ngrok.app", "ngrok-free.app", "trycloudflare.com", "loca.lt", "serveo.net")
BRANDS = ["sbi", "hdfc", "icici", "axis", "kotak", "pnb", "paytm", "phonepe", "gpay", "googlepay",
          "amazon", "flipkart", "irctc", "uidai", "aadhaar", "incometax", "epfo", "jio", "airtel"]
# TODO: verify and extend this allow-list. A link that mentions a brand but is not on one of
# these domains is treated as a look-alike.
OFFICIAL = ["sbi.co.in", "onlinesbi.sbi", "hdfcbank.com", "icicibank.com", "axisbank.com", "kotak.com",
            "pnbindia.in", "paytm.com", "phonepe.com", "pay.google.com", "google.com", "amazon.in",
            "amazon.com", "flipkart.com", "irctc.co.in", "uidai.gov.in", "incometax.gov.in",
            "incometaxindia.gov.in", "epfindia.gov.in", "jio.com", "airtel.in"]


def extract_urls(text: str) -> list[str]:
    return [u.rstrip(".,;:!?)") for u in URL_RE.findall(text)]


def _host(url: str) -> str:
    u = url if re.match(r"https?://", url, re.I) else "http://" + url
    return (urlparse(u).hostname or "").lower()


def _is_official(host: str) -> bool:
    return any(host == d or host.endswith("." + d) for d in OFFICIAL)


def link_signals(urls: list[str]) -> list[Signal]:
    found: dict[str, Signal] = {}
    for url in urls:
        host = _host(url)
        if not host:
            continue
        if host in SHORTENERS:
            found["short_link"] = Signal("short_link", "Uses a shortened link", 15,
                                         "Shortened links hide where you will really land.")
        if host.split(".")[-1] in SUSPICIOUS_TLDS:
            found["odd_tld"] = Signal("odd_tld", "Link ends in a cheap, unusual domain", 15,
                                      "Scam sites often use cheap endings like .xyz, .top, .click or .icu.")
        try:
            ipaddress.ip_address(host)
            found["ip_link"] = Signal("ip_link", "Link goes to a raw IP address", 25,
                                      "Genuine companies do not send links made of numbers.")
        except ValueError:
            pass
        tokens = re.split(r"[.\-_]", host)
        for b in BRANDS:
            hit = any(t == b or (len(b) > 3 and t.startswith(b)) for t in tokens)
            if hit and not _is_official(host):
                found["lookalike"] = Signal("lookalike", f"Link imitates a known brand ({b})", 35,
                                            "The link mentions a well-known brand but is not on its real website.")
                break
        if host.endswith(TUNNEL_HOSTS):
            found["tunnel_link"] = Signal("tunnel_link", "Link goes to a temporary tunnel address (ngrok and similar)", 25,
                                          "Free tunnel addresses are used to host throw-away fake pages. Banks and wallets never use them.")
        if host.count("-") >= 2:
            found["many_hyphens"] = Signal("many_hyphens", "Link has many hyphens", 10,
                                           "Long hyphenated names like 'bank-kyc-update-now' are typical of fake sites.")
    return list(found.values())


def normalize(text: str) -> str:
    """Undo common spelling tricks before the text rules run.

    Scammers write W0N, FL1PKART, V0DAF0NE or K.Y.C to dodge simple filters. We only change a
    0 or 1 that sits between two letters, so real numbers and links are left alone.
    """
    text = re.sub(r"\b([A-Za-z])\.([A-Za-z])\.([A-Za-z])\b", r"\1\2\3", text)  # K.Y.C -> KYC
    return re.sub(r"(?<=[A-Za-z])[01](?=[A-Za-z])", lambda m: "o" if m.group() == "0" else "i", text)


def text_signals(text: str) -> list[Signal]:
    text = normalize(text)
    sentences = [s for s in _SENT_SPLIT.split(text) if s.strip()]
    found: list[Signal] = []
    for sid, label, weight, why, patterns, sentence_level in _COMPILED:
        if sentence_level:
            hit = any(
                p.search(s) for s in sentences if not NEGATION.search(s) for p in patterns
            )
        else:
            hit = any(p.search(text) for p in patterns)
        if hit:
            found.append(Signal(sid, label, weight, why))
    return found
