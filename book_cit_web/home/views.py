from django.shortcuts import render
from .models import Book, Rating, Book_Topic
from django.contrib.auth.models import User
from django.http import HttpResponse
from .forms import searchForm
from .utils import normalize_vietnamese


# Logic xử lí
def checkRate(userid = None, bookid = None):
    rate = Rating.objects.filter(user_id = userid, book_id = bookid).first()
    if rate:
        return rate
    return 0

def rateBook(userid, bookid, point):
    rate = checkRate(userid=userid, bookid=bookid)
    if not rate:
        rate1 = Rating(user_id=userid, book_id = bookid, rating = point)
        rate1.save()
        return
    rate.rating = point
    rate.save()


# Ajax Response
def searchPost(request):
    skey = request.POST.get('skey')
    # Loại bỏ dấu câu của skey
    skey = normalize_vietnamese(skey)
    if len(skey)>=3:
        # sử dùng hàm __unaccent để có thể truy xuất băng tiếng việt không dấu
        books = Book.objects.filter(book_title__unaccent__icontains=skey)[:5]
        if books:
            context = ""
            # Chỉnh sửa phần context để hiển thị ra đúng
            for book in books:
                context+= f'<li><a href="/book/detail/id={book.book_id}">{ book.book_title }</a></li>'
            return HttpResponse(context)
        
    # có khả năng lỗi ở đây, lưu ý chọn giá trị return phù hợp
    return 

def searchTest(request):
    form = searchForm()
    context = {
        'form': form
    }
    return render(request, 'search.html', context)

                   
        
# Các view để trả về trang HTML theo url.
def index(request):
    bookList = {}
    bookList['popular'] = Book.objects.order_by('book_view')[0:10]  
    bookList['topVn'] = Book.objects.filter(book_lang = 'Vietnamese').order_by('book_view')[0:10]
    bookList['topFL'] = Book.objects.filter(book_lang = 'Foreign').order_by('book_view')[0:10]
    context = {
        'bookList' : bookList
    }
    return render(request, 'index.html', context)
    
def bookDetail(request, id):
    detail = Book.objects.filter(book_id = id).first()
    topicList = Book_Topic.objects.prefetch_related('topic_id').filter(book_id = detail.book_id)
    context = {
        'detail':detail,
        'topicList':topicList,
    }
    return render(request, 'bookDetail.html', context)

# pagepanigtion, su dung lai cau lenh truy xuat book o tren, 
def search(request):
    pass

def category(request):
    pass