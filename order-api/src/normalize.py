"""Turn whatever speech-to-text produced into plain ASCII digits.

Handles Chinese numerals (including 幺 / 洞 / 拐, as people read digits aloud
in Taiwan), full-width digits, spaces and dashes.
"""
import unicodedata

_CHINESE_DIGITS = {
    "零": "0", "〇": "0", "洞": "0",
    "一": "1", "幺": "1", "壹": "1",
    "二": "2", "兩": "2", "貳": "2",
    "三": "3", "參": "3",
    "四": "4", "肆": "4",
    "五": "5", "伍": "5",
    "六": "6", "陸": "6",
    "七": "7", "柒": "7", "拐": "7",
    "八": "8", "捌": "8",
    "九": "9", "玖": "9",
}


def to_digits(raw: str) -> str:
    text = unicodedata.normalize("NFKC", raw or "")
    out = []
    for ch in text:
        if "0" <= ch <= "9":
            out.append(ch)
        elif ch in _CHINESE_DIGITS:
            out.append(_CHINESE_DIGITS[ch])
    return "".join(out)


def normalize_order_id(raw: str) -> str | None:
    digits = to_digits(raw)
    return digits if len(digits) == 8 else None


def normalize_phone_last4(raw: str) -> str | None:
    digits = to_digits(raw)
    return digits if len(digits) == 4 else None
