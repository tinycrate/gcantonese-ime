#! python3

class GSuggestion:
    word = ""
    annotation = ""
    matched_length = 0
    def __init__(self, word, annotation, matched_length):
        self.word = word
        self.annotation = annotation
        self.matched_length = matched_length

class GRequest:
    request = ""
    suggestions = []
    requested_pages = 0
    max_pages = 32
    requested_time = 0

class GPage:
    word = ""
    page_num = 0
    suggestions = []
    def __init__(self, word, page_num, suggestions):
        self.word = word
        self.page_num = page_num
        self.suggestions = suggestions