from django.shortcuts import render
from .models import Book, Rating, Book_Topic, Topic, FavList, ContentBook
from django.http import HttpResponse, JsonResponse
from .forms import searchForm, SearchFormset
from .utils import normalize_vietnamese, pagePaginator, HTTPResponseHXRedirect, login_required
from django.shortcuts import redirect
import json
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg
import re
from functools import reduce
from operator import and_
from django.template.loader import render_to_string
from django.urls import reverse


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
        return str(result) + " người đánh giá"
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
        if 'paramslen' in request.session:
            del request.session['paramslen']
        return HTTPResponseHXRedirect(redirect_to='http://127.0.0.1:8000/searchAdvance')
    return

def categoryPost(request):
    topics = Topic.objects.all()
    context = None
    for topic in topics:
        context+= f'<li><a href="/category/filter/id={topic.topic_id - 3000}">{ topic.topic_name }</a></li>'
    return HttpResponse(context)

def ratingPost(request):
    # kiem tra nguoi dung da dang nhap chua khi nhan vao rating
    if not request.user.is_authenticated:
        login_url = reverse('login')  # URL của trang login
        current_url = request.POST.get('current_url', '/')
        return JsonResponse({"redirect": True, "url": f"{login_url}?next={current_url}"}, status=200)
    
    rate = request.POST.get('rate')
    book_id = request.POST.get('book_id')
    # ----------- Thêm hoặc cập nhật rating----------
    rating, created = Rating.objects.update_or_create(
        user_id = request.user.id,
        book_id = book_id,
        defaults={'rating' : rate}
    )
    hx_vals_data = json.dumps({"rate": int(rate),
                               "book_id": int(book_id),
                               })
    val = "rate-" + rate
    return HttpResponse(f'''
                        <input type="button" onclick="hidebutton(this)" name="clear" id="clear-rating" hx-post ='/clear_rating_post/' hx-trigger="click delay:0.25s" hx-target='#{val}' hx-swap = "outerHTML" value="Xóa đánh giá" hx-vals ='{hx_vals_data}'>
                        ''')

def ratingCheckPost(request):
    if not request.user.is_authenticated:
        return HttpResponse('')
    
    rate = request.POST.get('rate')
    book_id = request.POST.get('book_id')
    # ----------- Thêm hoặc cập nhật rating----------
    rating, created = Rating.objects.update_or_create(
        user_id = request.user.id,
        book_id = book_id,
        defaults={'rating' : rate}
    )
    hx_vals_data = json.dumps({"rate": int(rate),
                               "book_id": int(book_id),
                               })
    val = "rate-" + rate
    return HttpResponse(f'''
                        <input type="button" onclick="hidebutton(this)" name="clear" id="clear-rating" hx-post ='/clear_rating_post/' hx-trigger="click delay:0.25s" hx-target='#{val}' hx-swap = "outerHTML" value="Xóa đánh giá" hx-vals ='{hx_vals_data}'>
                        ''')

def clearRatingPost(request):
    rate = request.POST.get('rate')
    book_id = request.POST.get('book_id')
    
    # delete record rating
    Rating.objects.filter(user_id = request.user.id, book_id = book_id).delete()
    val = "rate-" + rate
    hx_vals_data = json.dumps({"rate": int(rate), "book_id": int(book_id)})
    return HttpResponse(f'''
                        <input type="radio" name="rating" id="{val}" hx-vals='{hx_vals_data}' hx-post ="/rating_post/" hx-trigger="click delay:0.25s" hx-target="#clear-rating" hx-swap="outerHTML">
                        ''')


# chay khi click vao button
def wishListPost(request):
    if not request.user.is_authenticated:
        login_url = reverse('login')  # URL của trang login
        current_url = request.POST.get('current_url', '/')
        current_url = current_url.replace('http://127.0.0.1:8000', '')
        print(f"{login_url}?next={current_url}")
        return JsonResponse({"redirect": True, "url": f"{login_url}?next={current_url}"}, status=200)
    user = request.user
    book_id = request.POST.get('book_id')
    hx_data = json.dumps({
        'book_id': book_id
    })
    
    check = FavList.objects.filter(user_id = user.id, book_id = book_id)
    # khi nhan vao -> kiem tra -> ko insert
    if not check:
        # thuc hien lenh insert
        fav = FavList(user_id = user.id, book_id=book_id)
        fav.save()
        # tra ve button saved
        return HttpResponse(f'''
                            <button class="wishlistStyle" hx-post = "/wishList_post/" hx-vals ='{hx_data}' hx-trigger="click delay:0.25s" hx-target='#wishlist{book_id}' hx-swap = 'innerHTML'><span style="color: green;">✓ </span>Đã Lưu</button>
                            ''')
    else:
        check.delete()
        return HttpResponse(f'''
                                <button class="wishlistStyle" hx-post = "/wishList_post/" hx-vals ='{hx_data}' hx-trigger="click delay:0.25s" hx-target='#wishlist{book_id}' hx-swap = 'innerHTML' onclick='savingList(this)'>Xem Sau</button>
                                ''')
# Chay khi load trang
def wishCheckPost(request):
    book_id = request.POST.get('book_id')
    hx_data = json.dumps({
        'book_id': book_id,
    })
    
    
    if not request.user.is_authenticated:
        return HttpResponse(f'''
                                <button class="btn-wishlist wishlistStyle" hx-post = "/wishList_post/" hx-vals ='{hx_data}' hx-trigger="click delay:0.25s" hx-target='#wishlist{book_id}' hx-swap = 'innerHTML' onclick='savingList(this)'>Xem Sau</button>
                                ''')
    
    check = FavList.objects.filter(user_id = request.user.id, book_id = book_id)
    if check: 
        return HttpResponse(f'''
                            <button class="btn-wishlist wishlistStyle" hx-post = "/wishList_post/" hx-vals ='{hx_data}' hx-trigger="click delay:0.25s" hx-target='#wishlist{book_id}' hx-swap = 'innerHTML'><span style="color: green;">✓ </span>Đã Lưu</button>
                            ''')
    return HttpResponse(f'''
                                <button class="btn-wishlist wishlistStyle" hx-post = "/wishList_post/" hx-vals ='{hx_data}' hx-trigger="click delay:0.25s" hx-target='#wishlist{book_id}' hx-swap = 'innerHTML' onclick='savingList(this)'>Xem Sau</button>
                                ''')

def topicListPost(request):
    topicList = Topic.objects.all().order_by('topic_name')
    context = ''
    for topic in topicList:
        context += f'<li><a class="dropdown-item" id="t-{int(topic.topic_id) - 3000}" href="/topicFilter/{str((topic.topic_id) - 3000)}/1">{topic.topic_name}</a></li>'
    return HttpResponse(context)


# middle logic
def searchSlug(request):
    query = request.GET.get('query')
    search_type = request.GET.get('search_type')
    query.replace(" ", "+")
    return redirect('search',search_type = search_type ,query = query, ftype = 5)
                   
# Các view để trả về trang HTML theo url.

def index(request):
    bookList = {}
    books_query = Book.objects.order_by('book_view')
    bookList['popular'] = books_query
    bookList['topVn'] = books_query.filter(book_lang = 'Vietnamese')
    bookList['topFl'] = books_query.filter(book_lang = 'Foreign')
    context = {
        'bookList' : bookList,
    }
    return render(request, 'index.html', context)
 
 
def myBook(request):
    bookList = {}
    if not request.user.is_authenticated:
        return redirect('login')
    from .models import FavList
    userID = request.user.id
    books = FavList.objects.filter(user_id=userID).select_related('book').order_by('-id')
    bookList = [fav.book for fav in books]
    
    countRates = {}
    averRates = {}
    for book in bookList:
        book_id = book.book_id
        countRates[book_id] = countRating(book_id=book_id)  # Lưu số lượng đánh giá của từng sách
        averRates[book_id] = averRating(book_id=book_id)
        
    # pagnition
    page_obj = pagePaginator(request, bookList) # Lấy đối tượng phân trang
    page_numbers = []
    
    # Hiển thị trang đầu, cuối, và các trang gần trang hiện tại
    for num in page_obj.paginator.page_range:
        if (
            num == 1 or 
            num == page_obj.paginator.num_pages or 
            abs(num - page_obj.number) <= 2  # Số trang gần trang hiện tại
        ):
            page_numbers.append(num)
        elif (
            abs(num - page_obj.number) == 3  # Thêm dấu "..." khi cần
            and num not in page_numbers
        ):
            page_numbers.append('...')
    
    context = {
        'page_obj' : page_obj,
        'page_numbers': page_numbers,
        'countRates': countRates,
        'averRates': averRates,
    }
    return render(request, 'myBook.html', context)   

def bookDetail(request, id):
    id += 3000
    
    books = Book.objects.all().order_by('book_id')
    detail = books.filter(book_id = id).first()
    topicList = Book_Topic.objects.prefetch_related('topic_id').filter(book_id = detail.book_id)
    # xử lý rating
    # truy xuất rating của cuốn sách, thêm checked vào radio của sao đã được rating, thêm nút clear rating
    Rate = None
    rating = None
    if request.user.is_authenticated:
        user_id = request.user.id
        Rate = Rating.objects.filter(user_id = user_id, book_id = id).first()
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
def search(request, search_type, query, ftype):
    form = searchForm()
    # Take skey and execute query
    query.replace('+',' ')
    query = normalize_vietnamese(query)
    pquery = query
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
    
    if ftype !=5:
        from home.utils import filterBasedType
        books = filterBasedType(books, ftype)  
        
    countRates = {}
    averRates = {}
    for book in books:
        book_id = book.book_id
        countRates[book_id] = countRating(book_id=book_id)  # Lưu số lượng đánh giá của từng sách
        averRates[book_id] = averRating(book_id=book_id)
    # pagnition
    page_obj = pagePaginator(request, books)
    page_numbers = []
    # Hiển thị trang đầu, cuối, và các trang gần trang hiện tại
    for num in page_obj.paginator.page_range:
        if (
            num == 1 or 
            num == page_obj.paginator.num_pages or 
            abs(num - page_obj.number) <= 2  # Số trang gần trang hiện tại
        ):
            page_numbers.append(num)
        elif (
            abs(num - page_obj.number) == 3  # Thêm dấu "..." khi cần
            and num not in page_numbers
        ):
            page_numbers.append('...')
    context = {
        'formSearch': form,
        'query': pquery,
        'search_type': search_type,
        'page_obj' : page_obj,
        'countRates': countRates,
        'averRates': averRates,
        'page_numbers': page_numbers,
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
    countRates = {}
    averRates = {}
    for book in books:
        book_id = book.book_id
        countRates[book_id] = countRating(book_id=book_id)  # Lưu số lượng đánh giá của từng sách
        averRates[book_id] = averRating(book_id=book_id)
    page_obj = pagePaginator(request, books)
    page_numbers = []
    # Hiển thị trang đầu, cuối, và các trang gần trang hiện tại
    for num in page_obj.paginator.page_range:
        if (
            num == 1 or 
            num == page_obj.paginator.num_pages or 
            abs(num - page_obj.number) <= 2  # Số trang gần trang hiện tại
        ):
            page_numbers.append(num)
        elif (
            abs(num - page_obj.number) == 3  # Thêm dấu "..." khi cần
            and num not in page_numbers
        ):
            page_numbers.append('...')
    context = {
        'tid': tid,
        'topicName': topicName,
        'page_obj': page_obj,
        'countRates': countRates,
        'averRates': averRates,
        'page_numbers': page_numbers,
    }
    # Cần thêm một html để hiển thị filter theo thể loại
    return render(request, 'filterBook.html', context)

def searchAdvance(request):
    formset = SearchFormset(request.POST or None)
    final_query = None
    queries = []
    subquery = Q()
    i = 1
    # Lưu các tham số tìm kiếm vào session nếu form hợp lệ
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
         
            # Lưu vào session
            request.session[f'search_params{i}'] = {
                'field_name': field_name,
                'search_type': search_type,
                'value': value
            }
            i += 1
        if queries:
            final_query = reduce(and_, queries)
            books = Book.objects.filter(final_query)
            request.session['paramslen'] = {
                'paramslen': i-1
            }
        else:
            books = Book.objects.all()
    else:
        # Lấy các tham số tìm kiếm từ session nếu tồn tại
        paramslen = request.session.get('paramslen')
        books = None
        if paramslen != None:
            for i in range(1,paramslen['paramslen']+1):
                search_params = request.session.get(f'search_params{i}')    
                
                field_name = search_params['field_name']
                search_type = search_params['search_type']
                value = search_params['value']
                
                keywords = re.split(r'[ ,]+', value)

                # Xây dựng lại query dựa trên session
                if search_type == 'iexact':
                    queries.append(Q(**{f"{field_name}__unaccent__iexact": value}))
                elif search_type == 'icontains':
                    subquery = Q(**{f"{field_name}__unaccent__icontains": keywords[0]})
                    for word in keywords[1:]:
                        subquery &= Q(**{f"{field_name}__unaccent__icontains": word})
                    queries.append(subquery)
                elif search_type == 'not_icontains':
                    subquery = ~Q(**{f"{field_name}__unaccent__icontains": keywords[0]})
                    for word in keywords[1:]:
                        subquery &= ~Q(**{f"{field_name}__unaccent__icontains": word})
                    queries.append(subquery)
            
            final_query = reduce(and_, queries)
            books = Book.objects.filter(final_query)
        else:
            books = Book.objects.all()
                
    # Phân trang
    page_obj = pagePaginator(request, books)
    page_numbers = []
    # Hiển thị trang đầu, cuối, và các trang gần trang hiện tại
    for num in page_obj.paginator.page_range:
        if (
            num == 1 or 
            num == page_obj.paginator.num_pages or 
            abs(num - page_obj.number) <= 2  # Số trang gần trang hiện tại
        ):
            page_numbers.append(num)
        elif (
            abs(num - page_obj.number) == 3  # Thêm dấu "..." khi cần
            and num not in page_numbers
        ):
            page_numbers.append('...')
    # Xử lý yêu cầu HTMX
    if request.headers.get('HX-Request'):
        html = render_to_string('advanceBooks.html', {'page_obj': page_obj, 'page_numbers': page_numbers})
        return HttpResponse(html)

    return render(request, 'searchAdvance.html', {'formset': formset, 'page_obj': page_obj, 'page_numbers': page_numbers})


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
    
    countRates = {}
    averRates = {}
    for book in books:
        book_id = book.book_id
        countRates[book_id] = countRating(book_id=book_id)  # Lưu số lượng đánh giá của từng sách
        averRates[book_id] = averRating(book_id=book_id)
        
    # phan trang
    page_obj = pagePaginator(request, books)
    page_numbers = []
    # Hiển thị trang đầu, cuối, và các trang gần trang hiện tại
    for num in page_obj.paginator.page_range:
        if (
            num == 1 or 
            num == page_obj.paginator.num_pages or 
            abs(num - page_obj.number) <= 2  # Số trang gần trang hiện tại
        ):
            page_numbers.append(num)
        elif (
            abs(num - page_obj.number) == 3  # Thêm dấu "..." khi cần
            and num not in page_numbers
        ):
            page_numbers.append('...')
    context = {
        'cid': cid,
        'page_obj': page_obj,
        'page_numbers': page_numbers,
        'countRates': countRates,
        'averRates': averRates,
    }
    return render(request, 'filterBook.html', context)