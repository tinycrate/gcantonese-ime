#! python3

from keycodes import * # for VK_XXX constants

symbols = {
    VK_OEM_MINUS: "\uff0d",
    VK_OEM_4: "\u3010",
    VK_OEM_6: "\u3011",
    VK_OEM_1: "\uff1b",
    VK_OEM_7: ["\u300c\u300d", False],
    VK_OEM_COMMA: "\uff0c",
    VK_OEM_PERIOD: "\u3002",
    VK_OEM_2: "\uff0f",
    VK_OEM_5: "\u3001",
}

symbols_shifted = {
    VK_OEM_3: "\uff5e",
    49: "\uff01",
    50: "\uff20",
    51: "\uff03",
    52: "\uffe5",
    54: "\u2026\u2026",
    55: "\uff06",
    56: "\u00d7",
    57: "\uff08",
    48: "\uff09",
    VK_OEM_MINUS: "\u2014\u2014",
    VK_OEM_4: "\uff5b",
    VK_OEM_6: "\uff5d",
    VK_OEM_1: "\uff1a",
    VK_OEM_7: ["\u300e\u300f", False],
    VK_OEM_COMMA: "\u300a",
    VK_OEM_PERIOD: "\u300b",
    VK_OEM_2: "\uff1f"
}

def is_symbol_pressed(keyEvent):
    if keyEvent.isKeyDown(VK_SHIFT):
        return keyEvent.keyCode in symbols_shifted
    else:
        return keyEvent.keyCode in symbols

def get_symbol(keyEvent):
    target = symbols_shifted if keyEvent.isKeyDown(VK_SHIFT) else symbols
    if keyEvent.keyCode in target:
        symbol = target[keyEvent.keyCode]
        if type(symbol) is list:
            switch = symbol[1]
            symbol[1] = not symbol[1]
            return symbol[0][int(switch)]
        else:
            return symbol