from django.shortcuts import render
from .models import Book, Rating, Book_Topic, Topic, FavList
from django.http import HttpResponse, JsonResponse
from .forms import searchForm
from .utils import normalize_vietnamese, pagePaginator
from django.shortcuts import redirect
import json
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg

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
    
def averRating(book_id):
    result = Rating.objects.filter(book_id=book_id).aggregate(ave=Avg('rating'))['ave']
    if result:
        return result
    return 0
def countRating(book_id):
    result = Rating.objects.filter(book_id=book_id).values('user_id').distinct().count()
    if result:
        return str(result) + "người đánh giá"
    return "Chưa có đánh giá"


# ---------Ajax Response--------
def searchPost(request):
    query = request.POST.get('query')
    search_type = request.POST.get('search_type')
    # Loại bỏ dấu câu của skey
    # Tach cau query thanh cac tu tim kiems
    query = normalize_vietnamese(query)
    if len(query)>=3:
        # sử dùng hàm __unaccent để có thể truy xuất băng tiếng việt không dấu
        # books = Book.objects.filter(book_title__unaccent__icontains=skey)[:5]
        # chinh sua o day
        if search_type == 'all':
            books = Book.objects.filter(
                Q(book_title__unaccent__icontains=query) |
                Q(book_author__unaccent__icontains=query) |
                Q(book_publish__unaccent__icontains=query)
            )
        else:
            books = Book.objects.filter(**{f"{search_type}__unaccent__icontains": query})
        books = books[:7]
        if books:
            context = ""
            # Chỉnh sửa phần context để hiển thị ra đúng
            for book in books:
                # chỉnh sủa để hiển thị suggest dựa theo từ khóa
                context+= f'<li><a href="/book/detail/id={book.book_id -3000}">{ book.book_title }</a></li>'
            return HttpResponse(context)
    return HttpResponse('')

def categoryPost(request):
    topics = Topic.objects.all()
    context = None
    for topic in topics:
        context+= f'<li><a href="/category/filter/id={topic.topic_id - 3000}">{ topic.topic_name }</a></li>'
    return HttpResponse(context)

# @login_required
def ratingPost(request):
    # insert rating vao database va hien thi nut clear rating
    rate = request.POST.get('rate')
    book_id = request.POST.get('book_id')
    # ----------- Thêm hoặc cập nhật rating----------
    # rating, created = Rating.objects.update_or_create(
    #     user_id = request.user.id,
    #     book_id = book_id,
    #     defaults={'rating' : rate}
    # )
    hx_vals_data = json.dumps({"rate": int(rate),
                               "book_id": int(book_id),
                               })
    val = "rate-" + rate
    return HttpResponse(f'''
                        <input type="button" onclick="hidebutton(this)" name="clear" id="clear" hx-post ='/clear_rating_post/' hx-trigger="click delay:0.25s" hx-target='#{val}' hx-swap = "outerHTML" value="Clear Rating" hx-vals ='{hx_vals_data}'>
                        ''')

def clearRatingPost(request):
    rate = request.POST.get('rate')
    book_id = request.POST.get('book_id')
    
    # delete record rating
    # Rating.objects.filter(user_id = request.user.id, book_id = book_id).delete()
    val = "rate-" + rate
    hx_vals_data = json.dumps({"rate": int(rate), "book_id": int(book_id)})
    return HttpResponse(f'''
                        <input type="radio" name="rating" id="{val}" hx-vals='{hx_vals_data}' hx-post ="/rating_post/" hx-trigger="click delay:0.25s" hx-target="#clear" hx-swap="outerHTML">
                        ''')
# @login_required
def wishListPost(request):
    book_id = request.POST.get('book_id')
    hx_data = json.dumps({
        'book_id': book_id
    })
    # user_id = request.user.id
    check = FavList.objects.filter(user_id = 1, book_id = book_id)
    # khi nhan vao -> kiem tra -> ko insert
    if not check:
        # thuc hien lenh insert
        fav = FavList(user_id = 1, book_id=book_id)
        fav.save()
        # tra ve button saved
        return HttpResponse(f'''
                            <button id='wishlist' hx-post = "/wishList_post/" hx-vals ='{hx_data}' hx-trigger="click delay:0.25s" hx-target='#wishlist' hx-swap = 'outerHTML'>Saved</button>
                            ''')
    else:
        check.delete()
        return HttpResponse(f'''
                                <button id='wishlist' hx-post = "/wishList_post/" hx-vals ='{hx_data}' hx-trigger="click delay:0.25s" hx-target='#wishlist' hx-swap = 'outerHTML' onclick='savingList(this)'>Want to read</button>
                                ''')

def wishCheckPost(request):
    book_id = request.POST.get('book_id')
    hx_data = json.dumps({
        'book_id': book_id
    })
    check = FavList.objects.filter(user_id = 1, book_id = book_id)
    if check: 
        return HttpResponse(f'''
                            <button id='wishlist' hx-post = "/wishList_post/" hx-vals ='{hx_data}' hx-trigger="click delay:0.25s" hx-target='#wishlist' hx-swap = 'outerHTML'>Saved</button>
                            ''')
    return HttpResponse(f'''
                                <button id='wishlist' hx-post = "/wishList_post/" hx-vals ='{hx_data}' hx-trigger="click delay:0.25s" hx-target='#wishlist' hx-swap = 'outerHTML' onclick='savingList(this)'>Want to read</button>
                                ''')
# middle logic
def searchSlug(request):
    query = request.GET.get('query')
    search_type = request.GET.get('search_type')
    query.replace(" ", "+")
    return redirect('search',search_type = search_type ,query = query)
                   
# Các view để trả về trang HTML theo url.
def index(request):
    forms = {}
    # thanh tim kiem
    forms['searchbar'] = searchForm()
    
    bookList = {}
    bookList['popular'] = Book.objects.order_by('book_view')[0:10]  
    bookList['topVn'] = Book.objects.filter(book_lang = 'Vietnamese').order_by('book_view')[0:10]
    bookList['topFL'] = Book.objects.filter(book_lang = 'Foreign').order_by('book_view')[0:10]
    context = {
        'bookList' : bookList,
        'forms' : forms,
    }
    return render(request, 'index.html', context)
    
def bookDetail(request, id):
    id += 3000
    detail = Book.objects.filter(book_id = id).first()
    topicList = Book_Topic.objects.prefetch_related('topic_id').filter(book_id = detail.book_id)
    # xử lý rating
    # truy xuất rating của cuốn sách, thêm checked vào radio của sao đã được rating, thêm nút clear rating
    user_id = 1 # user_id = request.user.id
    Rate = Rating.objects.filter(user_id = user_id, book_id = id).first()
    rating = None
    if Rate:
        rating = Rate.rating
    averRate = averRating(id)
    countRate = countRating(id)
    context = {
        'rating': str(rating),
        'detail':detail,
        'topicList':topicList,
        'averRate': averRate,
        'countRate': countRate,
    }
    return render(request, 'bookDetail.html', context)

# pagepanigtion, su dung lai cau lenh truy xuat book o tren, 
def search(request, search_type, query):
    form = searchForm()
    # Take skey and execute query
    query.replace('+',' ')
    query = normalize_vietnamese(query)
    if len(query)>=3:
        # sử dùng hàm __unaccent để có thể truy xuất băng tiếng việt không dấu
        # books = Book.objects.filter(book_title__unaccent__icontains=skey)[:5]
        # chinh sua o day
        if search_type == 'all':
            books = Book.objects.filter(
                Q(book_title__unaccent__icontains=query) |
                Q(book_author__unaccent__icontains=query) |
                Q(book_publish__unaccent__icontains=query)
            )
        else:
            books = Book.objects.filter(**{f"{search_type}__unaccent__icontains": query})
    # pagnition
    page_obj = pagePaginator(request, books)
    context = {
        'formSearch': form,
        'page_obj' : page_obj,
    }
    return render(request, 'searchBook.html', context)

def categoryFilter(request,id):
    id += 3000
    Book_TopicList = Book_Topic.objects.prefetch_related('topic_id').filter(topic_id = id)
    bookList = None
    topicTitle =False
    for book in Book_TopicList:
        if not topicTitle:
            topicTitle = book.topic_id.topic_name
        # Chinh sua hien thi cho cac quyen sach
        bookList+= f'<li><a href="/book/detail/id={book.book_id -3000}">{ book.book_id.book_title }</a></li>'
    context = {
        'topicTitle': topicTitle,
        'bookList': bookList
    }
    # Cần thêm một html để hiển thị filter theo thể loại
    return render(request, 'bookDetail.html', context)

    