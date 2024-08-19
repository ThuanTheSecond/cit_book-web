import unicodedata

def normalize_vietnamese(text):
    text = unicodedata.normalize('NFKD', text)
    rawText =  ''.join(c for c in text if not unicodedata.combining(c))
    rawText = rawText.replace('đ','d').replace('Đ', 'D')
    return rawText