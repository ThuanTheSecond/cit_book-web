import unicodedata
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponseRedirect


def normalize_vietnamese(text):
    text = unicodedata.normalize('NFKD', text)
    rawText =  ''.join(c for c in text if not unicodedata.combining(c))
    rawText = rawText.replace('đ','d').replace('Đ', 'D')
    return rawText

def pagePaginator(request, books):
    paginator = Paginator(books, 7)
    
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        # nếu số trang không phải số nguyên, load trang đầu tiên
        page_obj = paginator.page(1)
    except EmptyPage:
        # Nếu vượt qua trang cuối cùng, load trang cuối cùng
        page_obj = paginator.page(paginator.num_pages)
    return page_obj

class HTTPResponseHXRedirect(HttpResponseRedirect):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self['HX-Redirect']=self['Location']
    status_code = 200