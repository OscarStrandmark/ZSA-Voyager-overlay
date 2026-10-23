from .layout import ALIASES

NAMED = {
    "KC_ESCAPE": 1,
    "KC_MINUS": 12,
    "KC_EQUAL": 13,
    "KC_BSPACE": 14,
    "KC_TAB": 15,
    "KC_LBRACKET": 26,
    "KC_RBRACKET": 27,
    "KC_ENTER": 28,
    "KC_LCTRL": 29,
    "KC_SCOLON": 39,
    "KC_QUOTE": 40,
    "KC_GRAVE": 41,
    "KC_LSHIFT": 42,
    "KC_BSLASH": 43,
    "KC_COMMA": 51,
    "KC_DOT": 52,
    "KC_SLASH": 53,
    "KC_RSHIFT": 54,
    "KC_KP_ASTERISK": 55,
    "KC_LALT": 56,
    "KC_SPACE": 57,
    "KC_CAPSLOCK": 58,
    "KC_NUMLOCK": 69,
    "KC_SCROLLLOCK": 70,
    "KC_KP_7": 71,
    "KC_KP_8": 72,
    "KC_KP_9": 73,
    "KC_KP_MINUS": 74,
    "KC_KP_4": 75,
    "KC_KP_5": 76,
    "KC_KP_6": 77,
    "KC_KP_PLUS": 78,
    "KC_KP_1": 79,
    "KC_KP_2": 80,
    "KC_KP_3": 81,
    "KC_KP_0": 82,
    "KC_KP_DOT": 83,
    "KC_NONUS_BSLASH": 86,
    "KC_KP_ENTER": 96,
    "KC_RCTRL": 97,
    "KC_KP_SLASH": 98,
    "KC_PSCREEN": 99,
    "KC_RALT": 100,
    "KC_HOME": 102,
    "KC_UP": 103,
    "KC_PAGE_UP": 104,
    "KC_LEFT": 105,
    "KC_RIGHT": 106,
    "KC_END": 107,
    "KC_DOWN": 108,
    "KC_PAGE_DOWN": 109,
    "KC_INSERT": 110,
    "KC_DELETE": 111,
    "KC_AUDIO_MUTE": 113,
    "KC_AUDIO_VOL_DOWN": 114,
    "KC_AUDIO_VOL_UP": 115,
    "KC_KP_EQUAL": 117,
    "KC_PAUSE": 119,
    "KC_LGUI": 125,
    "KC_RGUI": 126,
    "KC_APPLICATION": 127,
    "KC_AGAIN": 129,
    "KC_UNDO": 131,
    "KC_COPY": 133,
    "KC_PASTE": 135,
    "KC_FIND": 136,
    "KC_CUT": 137,
    "KC_HELP": 138,
    "KC_MENU": 139,
    "KC_CALCULATOR": 140,
    "KC_SYSTEM_SLEEP": 142,
    "KC_MAIL": 155,
    "KC_WWW_BACK": 158,
    "KC_WWW_FORWARD": 159,
    "KC_MEDIA_NEXT_TRACK": 163,
    "KC_MEDIA_PLAY_PAUSE": 164,
    "KC_MEDIA_PREV_TRACK": 165,
    "KC_MEDIA_STOP": 166,
    "KC_WWW_REFRESH": 173,
    "KC_WWW_SEARCH": 217,
    "KC_BRIGHTNESS_DOWN": 224,
    "KC_BRIGHTNESS_UP": 225,
}

SHORT = {
    "KC_MINS": 12,
    "KC_EQL": 13,
    "KC_LBRC": 26,
    "KC_RBRC": 27,
    "KC_SCLN": 39,
    "KC_QUOT": 40,
    "KC_GRV": 41,
    "KC_BSLS": 43,
    "KC_COMM": 51,
    "KC_SLSH": 53,
}

SHIFTED = {
    "KC_EXLM": 2,
    "KC_AT": 3,
    "KC_HASH": 4,
    "KC_DLR": 5,
    "KC_PERC": 6,
    "KC_CIRC": 7,
    "KC_AMPR": 8,
    "KC_ASTR": 9,
    "KC_LPRN": 10,
    "KC_RPRN": 11,
    "KC_UNDS": 12,
    "KC_PLUS": 13,
    "KC_LCBR": 26,
    "KC_RCBR": 27,
    "KC_COLN": 39,
    "KC_DQUO": 40,
    "KC_TILD": 41,
    "KC_PIPE": 43,
    "KC_LABK": 51,
    "KC_RABK": 52,
    "KC_QUES": 53,
}

DIGITS = {"KC_1": 2, "KC_2": 3, "KC_3": 4, "KC_4": 5, "KC_5": 6, "KC_6": 7, "KC_7": 8, "KC_8": 9, "KC_9": 10, "KC_0": 11}

LETTERS = "QWERTYUIOP"
ROW_HOME = "ASDFGHJKL"
ROW_BOTTOM = "ZXCVBNM"

_LETTER_CODES = {}
for _offset, _letter in enumerate(LETTERS):
    _LETTER_CODES[_letter] = 16 + _offset
for _offset, _letter in enumerate(ROW_HOME):
    _LETTER_CODES[_letter] = 30 + _offset
for _offset, _letter in enumerate(ROW_BOTTOM):
    _LETTER_CODES[_letter] = 44 + _offset

_FUNCTION_CODES = {}
for _number in range(1, 11):
    _FUNCTION_CODES[f"F{_number}"] = 58 + _number
_FUNCTION_CODES["F11"] = 87
_FUNCTION_CODES["F12"] = 88
for _number in range(13, 25):
    _FUNCTION_CODES[f"F{_number}"] = 170 + _number


def needs_shift(qmk_code: str) -> bool:
    return ALIASES.get(qmk_code, qmk_code) in SHIFTED


def linux_code(qmk_code: str) -> int | None:
    if not qmk_code:
        return None
    code = ALIASES.get(qmk_code, qmk_code)
    if code in SHIFTED:
        return SHIFTED[code]
    if code in NAMED:
        return NAMED[code]
    if code in SHORT:
        return SHORT[code]
    if code in DIGITS:
        return DIGITS[code]
    body = code.removeprefix("KC_")
    if len(body) == 1 and body in _LETTER_CODES:
        return _LETTER_CODES[body]
    if body in _FUNCTION_CODES:
        return _FUNCTION_CODES[body]
    return None
