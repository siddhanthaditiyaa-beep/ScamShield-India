"""Regression tests from real-looking examples quoted on public pages (source=public_web).
Used for tuning, so passing them is NOT evidence of accuracy. See README, 'What has been measured'."""
from app.analyzer import analyze

SCAMS = [
    "प्रिय ग्राहक आज रात 8:30 बजे बिजली कार्यालय से आपकी बिजली काट दी जाएगी, क्योंकि आपका पिछले महीने का बिल अपडेट नहीं हुआ, कृपया तुरंत हमारे बिजली अधिकारी 9000000000 से संपर्क करें, धन्यवाद।",
    "प्रिय ग्राहक, आपका पेटीएम खाता ब्लॉक कर दिया गया है। कृपया अपना पैन कार्ड 24 घंटे के भीतर तुरंत अपडेट करें। यहां क्लिक करें",
    "प्रिय ग्राहक, आपका एसबीआई सेविंग अकाउंट 24 घंटे के भीतर ब्लॉक कर दिया जाएगा। इसे अनब्लॉक करने के लिए लिंक पर क्लिक करें",
    "प्रिय ग्राहक, तुमचे इंडिया पोस्ट पेमेंट बँक खाते आज ब्लॉक करण्यात आले आहे. कृपया तुमचे पॅन कार्ड येथे दिलेल्या लिंकवर क्लिक करून, त्वरित अपडेट करा.",
    "Dear Customer Your Electricity power will be disconnected Tonight at 8.30 pm from electricity office. because your previous month bill was not update please immediately call 9000000000",
]
GENUINE = [
    "बैंक ऑफ़ बड़ौदा कॉल, ई-मेल, एसएमएस और चैट सहित किसी भी माध्यम से कोई गोपनीय जानकारी नहीं मांगता है। कृपया अपना कार्ड नंबर, ओटीपी, पिन, सीवीवी, यूजर आईडी और पासवर्ड जैसी कोई भी महत्वपूर्ण जानकारी बैंक अधिकारियों सहित किसी के साथ साझा न करें।",
    "याद रखें, बैंक कभी भी पैन डिटेल, ओटीपी, यूपीआई, वीपीए / एमपीआईएन, कस्टमर आईडी और पासवर्ड, कार्ड नंबर, एटीएम पिन और सीवीवी नहीं मांगेगा। कृपया किसी के भी साथ अपनी गोपनीय डिटेल शेयर न करें।!",
    "प्रिय ग्राहक, तुमचे ऑर्डर पाठवले आहे. अधिक माहितीसाठी लिंकवर क्लिक करा.",
    "तुमचे बिजली बिल जमा झाले आहे. धन्यवाद.",
    "Your PAN card details have been updated. Thank you.",
]


def test_public_examples_reach_likely_scam():
    for t in SCAMS:
        assert analyze(t)["score"] >= 60, t


def test_genuine_warnings_and_receipts_stay_low():
    for t in GENUINE:
        assert analyze(t)["score"] < 30, t
