from django.shortcuts import render
from .models import Book, Rating, Book_Topic, Topic, FavList, ContentBook
from django.http import HttpResponse, JsonResponse
from .forms import searchForm, SearchFormset
from .utils import normalize_vietnamese, pagePaginator, HTTPResponseHXRedirect
from django.shortcuts import redirect
import json
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg
import re
from functools import reduce
from operator import and_
from django.template.loader import render_to_string


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
        keywords = re.split(r'[ ,]+', query)
        if search_type == 'all':
            query = Q()
            query = reduce(and_, (
                    Q(book_title__unaccent__icontains=word) |
                    Q(book_author__unaccent__icontains=word) |
                    Q(book_publish__unaccent__icontains=word)
                    for word in keywords
                    ))   
            books = Book.objects.filter(query)
        else:
            query = Q(**{f"{search_type}__unaccent__icontains": keywords[0]})
            for word in keywords[1:]:
                query &= Q(**{f"{search_type}__unaccent__icontains": word})
            books = Book.objects.filter(query)
        books = books[:7]
        if books:
            context = ""
            # Chỉnh sửa phần context để hiển thị ra đúng
            for book in books:
                # chỉnh sủa để hiển thị suggest dựa theo từ khóa
                context+= f'''
                <li><img class="search-book-image" src="{ book.bookImage.url }" alt="{ book.book_title }">
                <a href="/book/detail/id={book.book_id -3000}">{ book.book_title }</a></li>
                '''
            return HttpResponse(context)
    return HttpResponse('')

def searchTypePost(request):
    if request.POST.get('search_type') == 'advance':
          return HTTPResponseHXRedirect(redirect_to='http://127.0.0.1:8000/searchAdvance')
    return

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

def topicListPost(request):
    topicList = Topic.objects.all().order_by('topic_name')
    context = ''
    for topic in topicList:
        context += f'<li><a class="dropdown-item" id="t-{int(topic.topic_id) - 3000}" href="/topicFilter/{str((topic.topic_id) - 3000)}/1">{topic.topic_name}</a></li>'
    return HttpResponse(context)

def searchAdvancePost(request):
    pass


# middle logic
def searchSlug(request):
    query = request.GET.get('query')
    search_type = request.GET.get('search_type')
    query.replace(" ", "+")
    return redirect('search',search_type = search_type ,query = query)
                   
# Các view để trả về trang HTML theo url.
def index(request):
    bookList = {}
    books_query = Book.objects.order_by('book_view')
    bookList['popular'] = books_query[:10]  
    bookList['topVn'] = books_query.filter(book_lang = 'Vietnamese')[0:10]
    bookList['topFl'] = books_query.filter(book_lang = 'Foreign')[0:10]
    context = {
        'bookList' : bookList,
    }
    return render(request, 'index.html', context)
    
def bookDetail(request, id):
    id += 3000
    
    books = Book.objects.all().order_by('book_id')
    detail = books.filter(book_id = id).first()
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
    
    # lay goi y sach co noi dung tuong tu
    from .utils import getRecommend_content
    books_indexes = getRecommend_content(book_id= id)

    bookRecommendList = books.filter(book_id__in = books_indexes)

    context = {
        'rating': str(rating),
        'detail':detail,
        'topicList':topicList,
        'averRate': averRate,
        'countRate': countRate,
        'bookList': bookRecommendList,
    }
    return render(request, 'bookDetail.html', context)

# pagepanigtion, su dung lai cau lenh truy xuat book o tren, 
def search(request, search_type, query):
    form = searchForm()
    # Take skey and execute query
    query.replace('+',' ')
    query = normalize_vietnamese(query)
    pquery = query
    if len(query)>=3:
        # sử dùng hàm __unaccent để có thể truy xuất băng tiếng việt không dấu
        # books = Book.objects.filter(book_title__unaccent__icontains=skey)[:5]
        # chinh sua o day
        keywords = re.split(r'[ ,]+', query)
        if search_type == 'all':
            query = Q()
            query = reduce(and_, (
                    Q(book_title__unaccent__icontains=word) |
                    Q(book_author__unaccent__icontains=word) |
                    Q(book_publish__unaccent__icontains=word)
                    for word in keywords
                    ))   
            books = Book.objects.filter(query)
        else:
            query = Q(**{f"{search_type}__unaccent__icontains": keywords[0]})
            for word in keywords[1:]:
                query &= Q(**{f"{search_type}__unaccent__icontains": word})
            books = Book.objects.filter(query)
            
    # pagnition
    page_obj = pagePaginator(request, books)
    context = {
        'formSearch': form,
        'query': pquery,
        'search_type': search_type,
        'page_obj' : page_obj,
    }
    return render(request, 'searchBook.html', context)

def searchFilter(request, type):
    form = searchForm()
    query = request.GET.get('query',' ')
    search_type = request.GET.get('search_type', 'all')
    
    keywords = re.split(r'[ ,]+', query)
    if search_type == 'all':
        query = Q()
        query = reduce(and_, (
                Q(book_title__unaccent__icontains=word) |
                Q(book_author__unaccent__icontains=word) |
                Q(book_publish__unaccent__icontains=word)
                for word in keywords
                ))   
        books = Book.objects.filter(query)
    else:
        query = Q(**{f"{search_type}__unaccent__icontains": keywords[0]})
        for word in keywords[1:]:
            query &= Q(**{f"{search_type}__unaccent__icontains": word})
        books = Book.objects.filter(query)
        
    if type != 5:
        from home.utils import filterBasedType
        books = filterBasedType(request, books)
    print(books)    
    page_obj = pagePaginator(request, books)
    context = {
        'formSearch': form,
        'query': query,
        'page_obj' : page_obj,
    }
    return render(request, 'searchBook.html', context)


def topicFilter(request,tid, type = 1):
    from home.utils import filterBasedType
    id = int(tid) + 3000
    bookTopic = Book_Topic.objects.prefetch_related('topic_id').filter(topic_id = id)
    topicName = None
    bid = []
    for id in bookTopic:
        if topicName == None:
            topicName = id.topic_id.topic_name
        bid.append(id.book_id.book_id)
    books = Book.objects.filter(book_id__in = bid)

    # phan loai dua vao loc
    books = filterBasedType(books=books,type=type)

    page_obj = pagePaginator(request, books)
    context = {
        'tid': tid,
        'topicName': topicName,
        'page_obj': page_obj,
    }
    # Cần thêm một html để hiển thị filter theo thể loại
    return render(request, 'filterBook.html', context)

def searchAdvance(request):
    formset = SearchFormset(request.POST or None)
    page_obj = 'Yet'
    final_query = None
    queries = []
    subquery = Q()
    if formset.is_valid():
        for form in formset:
            field_name = form.cleaned_data.get('field_name')
            search_type = form.cleaned_data.get('search_type')
            value = form.cleaned_data.get('value')
            value = normalize_vietnamese(value)
            keywords = re.split(r'[ ,]+', value)
            
            if search_type == 'iexact':
                queries.append(Q(**{f"{field_name}__unaccent__iexact": value}))
            elif search_type == 'not_icontains':
                subquery = ~Q(**{f"{field_name}__unaccent__icontains": keywords[0]})
                for word in keywords[1:]:
                    subquery &= ~Q(**{f"{field_name}__unaccent__icontains": word})
                queries.append(subquery)
            elif search_type == 'icontains':
                subquery = Q(**{f"{field_name}__unaccent__icontains": keywords[0]})
                for word in keywords[1:]:
                    subquery &= Q(**{f"{field_name}__unaccent__icontains": word})
                queries.append(subquery)
                
        if queries:
            final_query = reduce(and_, queries)
            books = Book.objects.filter(final_query) 
            page_obj = pagePaginator(request, books)
            
    else:
        books = Book.objects.all()
        page_obj = pagePaginator(request, books)

    # Xử lý yêu cầu từ HTMX
    if request.headers.get('HX-Request'):
        html = render_to_string('advanceBooks.html', {'page_obj': page_obj})
        return HttpResponse(html)

    return render(request, 'searchAdvance.html', {'formset': formset, 'page_obj': page_obj})

def test(request):
    bookList = {}
    books_query = Book.objects.order_by('book_view')
    bookList['popular'] = books_query[:10]  
    bookList['topVn'] = books_query.filter(book_lang = 'Vietnamese')[0:10]
    bookList['topFL'] = books_query.filter(book_lang = 'Foreign')[0:10]
    books = Book.objects.order_by('book_view')[0:10]  
    context = {
        'bookList' : bookList,
        'books': books,
    }
    return render(request, 'test.html',context)

def categoryFilter(request,cid,type = 1):
    from home.utils import filterBasedType
    books = Book.objects.all()
    # phan loai dua vao category
    if cid != 'Trending':
        lang = 'Foreign'
        if cid == 'Tiếng Việt':
            lang = 'Vietnamese'
        books = books.filter(book_lang = lang)
    # phan loai dua vao loc
    books = filterBasedType(books=books,type=type)
    # phan trang
    page_obj = pagePaginator(request, books)
    context = {
        'cid': cid,
        'page_obj': page_obj
    }
    return render(request, 'filterBook.html', context)