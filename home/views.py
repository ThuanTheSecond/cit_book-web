from django.shortcuts import render, get_object_or_404
from .models import Book, Rating, Book_Topic, Topic, ToReads, ContentBook, BookViewHistory, BookReview
from django.http import HttpResponse, JsonResponse
from .forms import searchForm, SearchFormset, CategorySelectionForm
from .utils import normalize_vietnamese, get_content_based_recommendations,pagePaginator, HTTPResponseHXRedirect, login_required, get_recommendations
from django.shortcuts import redirect
import json
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg, Count, F, Sum, Value
from django.db.models.functions import Coalesce
import re
from functools import reduce
from operator import and_
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from home.tasks import finetune_svd_model_task

import logging

logger = logging.getLogger(__name__)

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
        return f"{result} đánh giá"
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
        
        # Lấy tổng số kết quả trước khi giới hạn
        total_results = books.count()
        # Giới hạn xuống 6 cuốn
        books = books[:6]
        
        if books:
            context = '<div class="search-suggestions-header"><i class="fas fa-search"></i> Gợi ý sách</div>'
            # Hiển thị cải tiến cho các gợi ý sách
            for book in books:
                context += f'''
                <div class="suggestion-item" onclick="window.location.href='/book/detail/id={book.book_id -3000}'">
                    <div class="suggestion-image">
                        <img src="{ book.bookImage.url }" alt="{ book.book_title }">
                    </div>
                    <div class="suggestion-info">
                        <div class="suggestion-title">{ book.book_title }</div>
                        <div class="suggestion-author"><i class="fas fa-pen-fancy"></i> { book.book_author }</div>
                    </div>
                    <div class="view-hint">
                        <i class="fas fa-eye"></i>
                    </div>
                </div>
                '''
            
            # Thêm nút "Xem tất cả kết quả" nếu có nhiều hơn 6 kết quả
            if total_results > 6:
                search_url = f"/searchSlug?search_type={search_type}&query={' '.join(keywords)}"
                context += f'''
                <div class="more-results">
                    <a href="{search_url}">
                        <span class="more-results-text">Xem tất cả {total_results} kết quả</span>
                        <i class="fas fa-arrow-right"></i>
                    </a>
                </div>
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
    from itertools import groupby
    from django.template.loader import render_to_string

    # Lấy tất cả topics và sắp xếp theo tên
    topics = Topic.objects.all().order_by('topic_name')
    
    # Nhóm topics theo chữ cái đầu tiên
    grouped_topics = {}
    for topic in topics:
        first_letter = topic.topic_name[0].upper()
        if first_letter not in grouped_topics:
            grouped_topics[first_letter] = []
        grouped_topics[first_letter].append(topic)
    
    # Sắp xếp các nhóm theo alphabet
    sorted_groups = dict(sorted(grouped_topics.items()))
    
    html = render_to_string('topic_groups.html', {
        'grouped_topics': sorted_groups
    })
    
    return HttpResponse(html)

def ratingPost(request):
    if not request.user.is_authenticated:
        login_url = reverse('login')
        current_url = request.POST.get('current_url', '/')
        current_url = current_url.replace('http://127.0.0.1:8000', '')
        return JsonResponse({"redirect": True, "url": f"{login_url}?next={current_url}"}, status=200)
    
    rate = request.POST.get('rate')
    book_id = request.POST.get('book_id')
    
    # Update or create rating
    rating, created = Rating.objects.update_or_create(
        user_id=request.user.id,
        book_id=book_id,
        defaults={'rating': rate}
    )
    
    logger.info(f"Saved rating for user {request.user.id}, book {book_id}, rating {rate}")
     
    # Check number of ratings
    rating_count = Rating.objects.filter(user=request.user).count()
    logger.info(f"User {request.user.id} has {rating_count} ratings")
    
    hx_vals_data = json.dumps({"rate": int(rate), "book_id": int(book_id)})
    val = f"rate-{rate}"    
    
    response_html = f'''
            <input type="button" onclick="hidebutton(this)" name="clear" id="clear-rating"
                   hx-post="/clear_rating_post/" hx-trigger="click delay:0.25s"
                   hx-target="#{val}" hx-swap="outerHTML" value="Xóa đánh giá"
                   hx-vals='{hx_vals_data}'>
        '''
        
    # If user has 5 or more ratings, trigger fine-tuning
    if rating_count == 5:
        if finetune_svd_model_task:
            try:
                finetune_svd_model_task.delay()
                logger.info("Fine-tuning task queued successfully")
            except Exception as e:
                logger.error(f"Failed to queue fine-tuning task: {e}")
        else:
            logger.warning("Fine-tuning task not available")
        
        # Add a flag in response to trigger the toast
        response_html += '<div style="display:none">You have rated enough books!</div>'
        
    return HttpResponse(response_html)   


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
        login_url = reverse('login')
        current_url = request.POST.get('current_url', '/')
        current_url = current_url.replace('http://127.0.0.1:8000', '')
        print(f"{login_url}?next={current_url}")
        return JsonResponse({"redirect": True, "url": f"{login_url}?next={current_url}"}, status=200)
    user = request.user
    book_id = request.POST.get('book_id')
    hx_data = json.dumps({
        'book_id': book_id
    })
    
    check = ToReads.objects.filter(user_id = user.id, book_id = book_id)
    if not check:
        fav = ToReads(user_id = user.id, book_id=book_id)
        fav.save()
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
    
    check = ToReads.objects.filter(user_id = request.user.id, book_id = book_id)
    if check: 
        return HttpResponse(f'''
                            <button class="btn-wishlist wishlistStyle" hx-post = "/wishList_post/" hx-vals ='{hx_data}' hx-trigger="click delay:0.25s" hx-target='#wishlist{book_id}' hx-swap = 'innerHTML'><span style="color: green;">✓ </span>Đã Lưu</button>
                            ''')
    return HttpResponse(f'''
                                <button class="btn-wishlist wishlistStyle" hx-post = "/wishList_post/" hx-vals ='{hx_data}' hx-trigger="click delay:0.25s" hx-target='#wishlist{book_id}' hx-swap = 'innerHTML' onclick='savingList(this)'>Xem Sau</button>
                                ''')

def topicListPost(request):
    from itertools import groupby
    from django.template.loader import render_to_string

    # Lấy tất cả topics và sắp xếp theo tên
    topics = Topic.objects.all().order_by('topic_name')
    
    # Nhóm topics theo chữ cái đầu tiên
    grouped_topics = {}
    for topic in topics:
        first_letter = topic.topic_name[0].upper()
        if first_letter not in grouped_topics:
            grouped_topics[first_letter] = []
        grouped_topics[first_letter].append(topic)
    
    # Sắp xếp các nhóm theo alphabet
    sorted_groups = dict(sorted(grouped_topics.items()))
    
    html = render_to_string('topic_groups.html', {
        'grouped_topics': sorted_groups
    })
    
    return HttpResponse(html)


# middle logic
def searchSlug(request):
    query = request.GET.get('query')
    search_type = request.GET.get('search_type')
    query.replace(" ", "+")
    return redirect('search',search_type = search_type ,query = query, ftype = 5)
                   
# Các view để trả về trang HTML theo url.
from django.contrib.auth.models import User
def index(request):
    bookList = {}
    
    # Lấy sách thịnh hành dựa trên kết hợp lượt xem và đánh giá
    # 1. Lấy sách có rating trung bình cao (≥ 4.0) và có ít nhất 5 lượt đánh giá
    from django.db.models import Count, Avg, F, ExpressionWrapper, FloatField, Q, Case, When, Value
    
    # Tính toán điểm phổ biến dựa trên công thức kết hợp lượt xem và đánh giá
    popular_books = Book.objects.annotate(
        avg_rating=Avg('rating__rating'),
        rating_count=Count('rating'),
        # Tính điểm phổ biến: (lượt xem * 0.7) + (đánh giá trung bình * số lượt đánh giá * 10 * 0.3)
        popularity_score=ExpressionWrapper(
            (F('book_view') * 0.7) + 
            (Coalesce(F('avg_rating'), Value(0)) * F('rating_count') * 10 * 0.3),
            output_field=FloatField()
        )
    ).order_by('-popularity_score')
    
    bookList['popular'] = popular_books[:10]
    bookList['topVn'] = Book.objects.filter(book_lang='Vietnamese').annotate(
        avg_rating=Avg('rating__rating'),
        rating_count=Count('rating'),
        popularity_score=ExpressionWrapper(
            (F('book_view') * 0.7) + 
            (Coalesce(F('avg_rating'), Value(0)) * F('rating_count') * 10 * 0.3),
            output_field=FloatField()
        )
    ).order_by('-popularity_score')[:10]
    
    bookList['topFl'] = Book.objects.filter(book_lang='Foreign').annotate(
        avg_rating=Avg('rating__rating'),
        rating_count=Count('rating'),
        popularity_score=ExpressionWrapper(
            (F('book_view') * 0.7) + 
            (Coalesce(F('avg_rating'), Value(0)) * F('rating_count') * 10 * 0.3),
            output_field=FloatField()
        )
    ).order_by('-popularity_score')[:10]

    # Truy xuất các giá trị thống kê
    total_books = Book.objects.count()
    total_users = User.objects.count()
    total_views = Book.objects.aggregate(Sum('book_view'))['book_view__sum'] or 0

    # Kiểm tra gợi ý cho người dùng đã đăng nhập
    recommended_books = []
    show_recommendations = False
    if request.user.is_authenticated:
        rating_count = Rating.objects.filter(user=request.user).count()
        if rating_count >= 5:
            recommended_books = get_recommendations(request.user.id, num_recommendations=10)
            if recommended_books:
                show_recommendations = True
                logger.info(f"Đã tạo gợi ý cho user {request.user.id}: {len(recommended_books)} sách")

    context = {
        'bookList': bookList,
        'recommended_books': recommended_books,
        'show_recommendations': show_recommendations,
        'total_books': total_books,
        'total_users': total_users,
        'total_views': total_views,
    }
    return render(request, 'index_modern.html', context) 
 
def myBook(request):
    bookList = {}
    if not request.user.is_authenticated:
        return redirect('login')
    from .models import ToReads
    userID = request.user.id
    books = ToReads.objects.filter(user_id=userID).select_related('book').order_by('-id')
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
    detail = get_object_or_404(Book, book_id=id+3000)
    
    # Update or create view history if user is authenticated
    if request.user.is_authenticated:
        BookViewHistory.objects.update_or_create(
            user=request.user,
            book=detail,
            defaults={'viewed_at': timezone.now()}
        )
        
        # Get user's rating
        user_rating = Rating.objects.filter(
            user=request.user, 
            book=detail
        ).first()
        
        rating = str(user_rating.rating) if user_rating else 'None'
        
        # Check if user has already reviewed
        user_has_reviewed = BookReview.objects.filter(
            user=request.user, 
            book=detail
        ).exists()
    else:
        user_has_reviewed = False
        rating = 'None'

    # Increment view count
    detail.book_view = F('book_view') + 1
    detail.save()

    # Get ratings statistics
    rating_stats = Rating.objects.filter(book=detail).aggregate(
        average=Avg('rating'),
        count=Count('id')
    )
    
    averRate = "{:.1f}".format(rating_stats['average'] or 0)
    countRate = rating_stats['count']

    # Get reviews for comments only
    reviews = BookReview.objects.filter(book=detail)\
        .select_related('user')\
        .order_by('-created_at')

    # Get book topics
    book_topics = Book_Topic.objects.filter(book_id=detail)\
        .select_related('topic_id')
    topics = [
        {'topic_id': bt.topic_id.topic_id, 'topic_name': bt.topic_id.topic_name} 
        for bt in book_topics
    ]

    # Get similar books
    similar_books = get_content_based_recommendations(detail.book_id, 10)

    # Get all reviews for this book
    reviews = detail.reviews.select_related('user').all()
    
    # Get ratings for all users who reviewed
    ratings = {
        str(rating.user_id): rating.rating  # Convert user_id to string
        for rating in Rating.objects.filter(
            book=detail,
            user_id__in=reviews.values_list('user_id', flat=True)
        )
    }
    
    context = {
        'detail': detail,
        'rating': rating,
        'averRate': averRate,
        'countRate': countRate,
        'bookList': similar_books,
        'user_has_reviewed': user_has_reviewed,
        'reviews': reviews,
        'book_topics': topics,
        'ratings': ratings,
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
    
    print(ftype)
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
        'type': ftype,
    }
    return render(request, 'searchBook.html', context)

def topicFilter(request, tid, type=1):
    from home.utils import filterBasedType
    
    # Lấy topic trực tiếp từ database
    topic = get_object_or_404(Topic, topic_id=tid)
    topicName = topic.topic_name
    
    # Lấy danh sách sách thuộc topic
    bookTopic = Book_Topic.objects.filter(topic_id=tid)
    bid = [bt.book_id.book_id for bt in bookTopic]
    
    # Lấy tất cả sách có id trong danh sách bid
    books = Book.objects.filter(book_id__in=bid)
    
    # Kiểm tra và lọc sách
    if not books.exists():
        books = []
    else:
        # Phân loại dựa vào filter type
        books = filterBasedType(books=books, type=type)
    
    countRates = {}
    averRates = {}
    for book in books:
        book_id = book.book_id
        countRates[book_id] = countRating(book_id=book_id)
        averRates[book_id] = averRating(book_id=book_id)
    
    # Xử lý phân trang
    page_obj = pagePaginator(request, books)
    page_numbers = []
    if page_obj:
        for num in page_obj.paginator.page_range:
            if (
                num == 1 or 
                num == page_obj.paginator.num_pages or 
                abs(num - page_obj.number) <= 2
            ):
                page_numbers.append(num)
            elif (
                abs(num - page_obj.number) == 3
                and num not in page_numbers
            ):
                page_numbers.append('...')

    context = {
        'tid': tid,
        'topicName': topicName,  # Luôn có giá trị, kể cả khi không có sách
        'page_obj': page_obj,
        'countRates': countRates,
        'averRates': averRates,
        'page_numbers': page_numbers,
        'filter_type': type,
    }
    return render(request, 'filterBook.html', context)

def searchAdvance(request):
    formset = SearchFormset(request.POST or None)
    category_form = CategorySelectionForm(request.POST or None)
    final_query = None
    queries = []
    i = 1
    
    # Lấy danh sách topics từ model Topic
    topics = Topic.objects.filter(is_active=True).order_by('topic_name').values('topic_id', 'topic_name')

    if request.method == 'POST':
        formset_valid = formset.is_valid()
        category_valid = category_form.is_valid()
        
        if formset_valid and category_valid:
            # Lấy selected_categories từ category_form
            selected_categories_str = category_form.cleaned_data.get('selected_categories', '')
            selected_categories = []
            
            print(f"POST request với selected_categories_str: {selected_categories_str}")
            
            # Tạo query cho thể loại
            category_query = None
            if selected_categories_str:
                try:
                    selected_categories = json.loads(selected_categories_str)
                    logger.info(f"Đã parse selected_categories: {selected_categories}")
                    
                    if selected_categories:
                        # Tạo query AND cho tất cả các thể loại đã chọn
                        # Lấy danh sách book_id cho từng thể loại
                        category_queries = []
                        for topic_id in selected_categories:
                            # Lấy danh sách book_id cho thể loại này
                            book_ids = Book_Topic.objects.filter(topic_id=topic_id).values_list('book_id', flat=True)
                            category_queries.append(Q(book_id__in=book_ids))
                        
                        # Kết hợp các query bằng phép AND
                        if category_queries:
                            category_query = category_queries[0]
                            for query in category_queries[1:]:
                                category_query &= query
                except json.JSONDecodeError:
                    pass
            
            # Tạo query cho từ khóa
            keyword_queries = []
            for form in formset:
                field_name = form.cleaned_data.get('field_name')
                search_type = form.cleaned_data.get('search_type')
                value = form.cleaned_data.get('value')
                
                if value:  # Chỉ xử lý nếu có giá trị nhập vào
                    value = normalize_vietnamese(value)
                    keywords = re.split(r'[ ,]+', value)
                    
                    if search_type == 'iexact':
                        keyword_queries.append(Q(**{f"{field_name}__unaccent__iexact": value}))
                    elif search_type == 'icontains':
                        subquery = Q(**{f"{field_name}__unaccent__icontains": keywords[0]})
                        for word in keywords[1:]:
                            subquery &= Q(**{f"{field_name}__unaccent__icontains": word})
                        keyword_queries.append(subquery)
                    elif search_type == 'not_icontains':
                        subquery = ~Q(**{f"{field_name}__unaccent__icontains": keywords[0]})
                        for word in keywords[1:]:
                            subquery &= ~Q(**{f"{field_name}__unaccent__icontains": word})
                        keyword_queries.append(subquery)
                
                # Lưu tham số tìm kiếm vào session
                request.session[f'search_params{i}'] = {
                    'field_name': field_name,
                    'search_type': search_type,
                    'value': value
                }
                i += 1
            
            # Lưu thể loại đã chọn vào session
            request.session['selected_categories'] = selected_categories_str
            
            # Kết hợp các query từ khóa bằng phép OR
            keyword_query = None
            if keyword_queries:
                keyword_query = reduce(and_, keyword_queries)
            
            # Kết hợp query thể loại và query từ khóa bằng phép AND
            final_query = None
            if category_query and keyword_query:
                final_query = category_query & keyword_query
                logger.info("Kết hợp tìm kiếm theo thể loại VÀ từ khóa")
            elif category_query:
                final_query = category_query
                logger.info("Chỉ tìm kiếm theo thể loại")
            elif keyword_query:
                final_query = keyword_query
                logger.info("Chỉ tìm kiếm theo từ khóa")
            
            # Thực hiện truy vấn
            if final_query:
                books = Book.objects.filter(final_query)
                logger.info(f"SQL Query: {str(books.query)}")
                logger.info(f"Số lượng sách tìm thấy: {books.count()}")
            else:
                # Nếu không có điều kiện tìm kiếm nào, hiển thị tất cả sách
                logger.info("Không có query nào được tạo, hiển thị tất cả sách")
                books = Book.objects.all()
            
            request.session['paramslen'] = {
                'paramslen': i-1
            }
        else:
            # Form không hợp lệ, kiểm tra xem có giá trị tìm kiếm hoặc thể loại không
            has_search_value = any(form.cleaned_data.get('value') for form in formset if hasattr(form, 'cleaned_data'))
            has_categories = False
            
            try:
                selected_categories = request.POST.get('selected_categories', '')
                if selected_categories:
                    categories = json.loads(selected_categories)
                    has_categories = bool(categories)
            except (json.JSONDecodeError, TypeError):
                pass
            
            if not has_search_value and not has_categories:
                # Không có giá trị tìm kiếm và không có thể loại, hiển thị thông báo lỗi
                messages.error(request, "Vui lòng nhập ít nhất một giá trị tìm kiếm hoặc chọn ít nhất một thể loại")
                return render(request, 'searchAdvance.html', {
                    'formset': formset,
                    'category_form': category_form,
                    'topics': list(topics)
                })
            
            # Nếu có giá trị tìm kiếm hoặc thể loại nhưng form không hợp lệ vì lý do khác
            # Hiển thị tất cả sách
            books = Book.objects.all()
    else:
        # Lấy các tham số tìm kiếm từ session nếu tồn tại
        paramslen = request.session.get('paramslen')
        selected_categories_str = request.session.get('selected_categories', '')
        selected_categories = []
        
        # Tạo query cho thể loại
        category_query = None
        if selected_categories_str:
            try:
                selected_categories = json.loads(selected_categories_str)
                
                if selected_categories:
                    # Lấy danh sách book_id từ Book_Topic dựa trên topic_id
                    book_ids = Book_Topic.objects.filter(topic_id__in=selected_categories).values_list('book_id', flat=True)
                    
                    # Tạo query cho thể loại
                    if book_ids:
                        category_query = Q(book_id__in=book_ids)
            except json.JSONDecodeError:
                pass
        
        # Tạo query cho từ khóa
        keyword_queries = []
        if paramslen:
            for i in range(1, paramslen['paramslen']+1):
                search_params = request.session.get(f'search_params{i}')
                if not search_params:
                    continue
                
                field_name = search_params.get('field_name')
                search_type = search_params.get('search_type')
                value = search_params.get('value')
                
                if value:
                    value = normalize_vietnamese(value)
                    keywords = re.split(r'[ ,]+', value)
                    
                    if search_type == 'iexact':
                        keyword_queries.append(Q(**{f"{field_name}__unaccent__iexact": value}))
                    elif search_type == 'icontains':
                        subquery = Q(**{f"{field_name}__unaccent__icontains": keywords[0]})
                        for word in keywords[1:]:
                            subquery &= Q(**{f"{field_name}__unaccent__icontains": word})
                        keyword_queries.append(subquery)
                    elif search_type == 'not_icontains':
                        subquery = ~Q(**{f"{field_name}__unaccent__icontains": keywords[0]})
                        for word in keywords[1:]:
                            subquery &= ~Q(**{f"{field_name}__unaccent__icontains": word})
                        keyword_queries.append(subquery)
        
        # Kết hợp các query từ khóa bằng phép OR
        keyword_query = None
        if keyword_queries:
            keyword_query = reduce(and_, keyword_queries)
        
        # Kết hợp query thể loại và query từ khóa bằng phép AND
        final_query = None
        if category_query and keyword_query:
            final_query = category_query & keyword_query
            logger.info("Kết hợp tìm kiếm theo thể loại VÀ từ khóa")
        elif category_query:
            final_query = category_query
            logger.info("Chỉ tìm kiếm theo thể loại")
        elif keyword_query:
            final_query = keyword_query
            logger.info("Chỉ tìm kiếm theo từ khóa")
        
        # Thực hiện truy vấn
        if final_query:
            books = Book.objects.filter(final_query)
            logger.info(f"SQL Query (từ session): {str(books.query)}")
            logger.info(f"Số lượng sách tìm thấy (từ session): {books.count()}")
        else:
            books = Book.objects.all() 
    #lay rate
    countRates = {}
    averRates = {}
    for book in books:
        book_id = book.book_id
        countRates[book_id] = countRating(book_id=book_id)
        averRates[book_id] = averRating(book_id=book_id)               
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

    # Truyền danh sách topics vào template
    return render(request, 'searchAdvance.html', {
        'formset': formset, 
        'category_form': category_form,
        'page_obj': page_obj, 
        'page_numbers': page_numbers,
        'countRates': countRates,
        'averRates': averRates,
        'topics': list(topics)  # Chuyển QuerySet thành list để có thể serialize trong template
    })


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

def categoryFilter(request, cid, type=1):
    from home.utils import filterBasedType
    books = Book.objects.all()
    cateName = 'Sách Thịnh Hành'
    # Phân loại dựa vào category
    if cid == 'Recommended':
        if not request.user.is_authenticated:
            return redirect('login')
        rating_count = Rating.objects.filter(user=request.user).count()
        if rating_count < 5:
            messages.info(request, "Bạn cần đánh giá ít nhất 5 cuốn sách để nhận được gợi ý")
            return redirect('home')
        books = get_recommendations(request.user.id, num_recommendations=20)
        cateName = 'Sách Gợi Ý Cho Bạn'
    elif cid != 'Trending':
        lang = 'Foreign'
        cateName='Sách Ngoại Văn'
        if cid == 'Tiếng Việt':
            lang = 'Vietnamese'
            cateName = 'Sách Tiếng Việt'
        books = books.filter(book_lang=lang)
    
    # Phân loại dựa vào filter type
    if cid != 'Recommended':  # Không áp dụng filter cho sách gợi ý
        books = filterBasedType(books=books, type=type)
    
    # Kiểm tra nếu không có sách
    if not books:
        books = []
    
    countRates = {}
    averRates = {}
    for book in books:
        book_id = book.book_id
        countRates[book_id] = countRating(book_id=book_id)
        averRates[book_id] = averRating(book_id=book_id)
    
    # Phân trang
    page_obj = pagePaginator(request, books)
    page_numbers = []
    if page_obj:
        for num in page_obj.paginator.page_range:
            if num == 1 or num == page_obj.paginator.num_pages or abs(num - page_obj.number) <= 2:
                page_numbers.append(num)
            elif abs(num - page_obj.number) == 3 and num not in page_numbers:
                page_numbers.append('...')

    context = {
        'cid': cid,
        'cateName': cateName,
        'page_obj': page_obj,
        'page_numbers': page_numbers,
        'countRates': countRates,
        'averRates': averRates,
        'filter_type': type
    }
    return render(request, 'filterBook.html', context)

@login_required
def view_history(request):
    # Get user's view history, ordered by most recent
    history_list = BookViewHistory.objects.filter(
        user=request.user
    ).select_related('book').order_by('-viewed_at')

    context = {
        'history_list': history_list,
    }
    return render(request, 'view_history.html', context)

@login_required
def profile(request):
    # Get user's statistics
    books_viewed = BookViewHistory.objects.filter(user=request.user).count()
    books_rated = Rating.objects.filter(user=request.user).count()
    books_saved = ToReads.objects.filter(user=request.user).count()

    # Get user's view history
    history_list = BookViewHistory.objects.filter(
        user=request.user
    ).select_related('book').order_by('-viewed_at')[:12]
    
    # Get user's wishlist books
    wishlist_books = [toreads.book for toreads in ToReads.objects.filter(
        user=request.user
    ).select_related('book').order_by('-created_at')]

    # Get user's rated books
    rated_books = Rating.objects.filter(
        user=request.user
    ).select_related('book').order_by('-created_at')

    context = {
        'books_viewed': books_viewed,
        'books_rated': books_rated,
        'books_saved': books_saved,
        'history_list': history_list,
        'wishlist_books': wishlist_books,
        'rated_books': rated_books,
    }
    return render(request, 'profile.html', context)

@login_required
def add_review(request, book_id):
    if request.method == 'POST':
        book = get_object_or_404(Book, book_id=book_id)
        comment = request.POST.get('comment')

        review, created = BookReview.objects.update_or_create(
            user=request.user,
            book=book,
            defaults={
                'comment': comment,
                'rating': None
            }
        )

        if request.headers.get('HX-Request'):
            reviews = book.reviews.select_related('user').all()
            # Lấy ratings cho tất cả users đã review
            ratings = {
                rating.user_id: rating.rating 
                for rating in Rating.objects.filter(
                    book=book,
                    user_id__in=reviews.values_list('user_id', flat=True)
                )
            }
            return render(request, 'partials/reviews_list.html', {
                'reviews': reviews,
                'ratings': ratings
            })
        
        return redirect('book_detail', id=book_id)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)
