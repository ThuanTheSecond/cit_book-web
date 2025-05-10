from django.http import HttpResponseRedirect
def normalize_vietnamese(text):
    import unicodedata
    text = unicodedata.normalize('NFKD', text)
    rawText =  ''.join(c for c in text if not unicodedata.combining(c))
    rawText = rawText.replace('đ','d').replace('Đ', 'D')
    return rawText

def pagePaginator(request, books):
    from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
    paginator = Paginator(books, 5)
    
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


from django.contrib.auth import REDIRECT_FIELD_NAME
from django.conf import settings
from django.contrib.auth.decorators import login_required as django_login_required
from django.http import HttpResponse
from functools import wraps

from django.shortcuts import resolve_url


def login_required(function=None, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    @wraps(function)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated and request.htmx:
            return HTTPResponseHXRedirect(redirect_to='http://127.0.0.1:8000/account/login')
        return django_login_required(
            function=function,
            login_url=login_url,
            redirect_field_name=redirect_field_name
        )(request, *args, **kwargs)
    return wrapper



# Thêm mới record vào ContentBook
def createBookContent(book_instance):
    from home.models import ContentBook, Book_Topic
    from django.db import transaction
    
    # Đảm bảo transaction đã hoàn tất
    with transaction.atomic():
        # Refresh instance để đảm bảo dữ liệu mới nhất
        book_instance.refresh_from_db()
        
        # Sử dụng trực tiếp instance
        content = str(book_instance.book_title)
        
        # Lấy topics của sách cụ thể này
        topics = Book_Topic.objects.filter(book_id=book_instance).select_related('topic_id')
        
        for topic in topics:
            content += f" {topic.topic_id.topic_name}"
        
        content += f" {book_instance.book_author}"
        
        # Tạo ContentBook với instance sách đã có
        newContent, created = ContentBook.objects.get_or_create(
            book=book_instance,
            defaults={'content': content}
        )
        
        if created:
            print(f"Created ContentBook for book: {book_instance.book_title} (ID: {book_instance.book_id})")
        else:
            # Nếu đã tồn tại, cập nhật content
            newContent.content = content
            newContent.save()
            print(f"Updated existing ContentBook for book: {book_instance.book_title} (ID: {book_instance.book_id})")
            
        return newContent

# Cập nhật nội dung trong table ContentBook
def updateBookContent(book_instance):
    from home.models import ContentBook, Book_Topic
    from django.db import transaction
    
    # Đảm bảo transaction đã hoàn tất
    with transaction.atomic():
        # Refresh instance để đảm bảo dữ liệu mới nhất
        book_instance.refresh_from_db()
        
        # Sử dụng trực tiếp instance
        content = str(book_instance.book_title)
        
        # Lấy topics của sách cụ thể này
        topics = Book_Topic.objects.filter(book_id=book_instance).select_related('topic_id')
        
        for topic in topics:
            content += f" {topic.topic_id.topic_name}"
        
        content += f" {book_instance.book_author}"
        
        try:
            # Cập nhật ContentBook với instance sách đã có
            content_update, created = ContentBook.objects.update_or_create(
                book=book_instance,
                defaults={'content': content}
            )
            print(f"{'Created' if created else 'Updated'} ContentBook for book: {book_instance.book_title} (ID: {book_instance.book_id})")
            return content_update
        except Exception as e:
            print(f"Error updating ContentBook for book: {book_instance.book_title}")
            print(f"Error details: {str(e)}")
            return None

# cập nhật ma trận consine_similarity (không dùng nữa)
def updateContentRecommend():
    from home.models import ContentBook
    from sklearn.metrics.pairwise import linear_kernel
    import pickle
    import pandas as pd
    
    # open tfidf.pkl to load book_tfidf
    with open('./home/recommend/book_tfidf_vectorizer.pkl', 'rb') as f:
        book_tfidf = pickle.load(f)
        
    # load tạo dataframe cho ContentBook cũ  
    bookContents = ContentBook.objects.all().order_by('book_id').values('book_id', 'content')
    book_df = pd.DataFrame(bookContents)
    book_df['content'] = book_df['content'].fillna('')
    book_df['content'] = book_df['content'].astype(str)

    # Vector hóa nội dung sách mới
    book_content_matrix = book_tfidf.fit_transform(book_df['content'])        
    # Cập nhật ma trận cosine similarity cho toàn bộ hệ thống
    cosine_similarity = linear_kernel(book_content_matrix, book_content_matrix)

    # Lưu TF-IDF Vectorizer
    with open('./home/recommend/book_cosine_similarity.pkl', 'wb') as f:
        pickle.dump(cosine_similarity, f)
    print('updated content after delete')

def getRecommend_content(book_id):
    from home.models import ContentBook
    from sklearn.metrics.pairwise import linear_kernel
    import pickle
    import pandas as pd
    
    bookContents = ContentBook.objects.all().order_by('book_id').values('book_id', 'content')
    book_df = pd.DataFrame(bookContents)
    book_df['content'] = book_df['content'].fillna('')
    # Thao tac de truy xuat index cua book_id trong dataframe book_df
    book_df.set_index('book_id', inplace=True)
    book_index = book_df.index.get_loc(book_id)
    
    with open('./home/recommend/book_tfidf_vectorizer.pkl', 'rb') as f:
        book_tfidf = pickle.load(f) 
    
    book_content_matrix = book_tfidf.fit_transform(book_df['content']) 
    cosine_similarity = linear_kernel(book_content_matrix, book_content_matrix)

    choice = book_index
    similarity_scores = list(enumerate(cosine_similarity[choice]))
    similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)
    similarity_scores = similarity_scores[1:9]

    # Get the similar books index
    books_index = [i[0] for i in similarity_scores]
    books_index_real = []
    for i in books_index:
        books_index_real.append(i+3000+1) 
    print(books_index_real)
    return books_index_real
    
def filterBasedType(books, type):
    
    if type == 1:
        # Thay đổi từ sắp xếp theo lượt xem sang sắp xếp theo độ phổ biến
        from django.db.models import Avg, Count, F, ExpressionWrapper, FloatField, Value
        from django.db.models.functions import Coalesce
        
        books = books.annotate(
            avg_rating=Avg('rating__rating'),
            rating_count=Count('rating'),
            # Tính điểm phổ biến: (lượt xem * 0.7) + (đánh giá trung bình * số lượt đánh giá * 10 * 0.3)
            popularity_score=ExpressionWrapper(
                (F('book_view') * 0.7) + 
                (Coalesce(F('avg_rating'), Value(0)) * F('rating_count') * 10 * 0.3),
                output_field=FloatField()
            )
        ).order_by('-popularity_score')
    elif type == 2:
        from django.db.models import IntegerField, Value
        from django.db.models.functions import Cast, Substr, Length, Coalesce
        from django.db.models import F
        import re

        def extract_year(publish_str):
            # Tìm năm trong chuỗi có dạng "... (2023)" hoặc "... 2023"
            year_pattern = r'.*?(\d{4})\)?$'
            match = re.search(year_pattern, publish_str or '')
            return int(match.group(1)) if match else 0

        books = books.annotate(
            # Trích xuất năm từ book_publish sử dụng custom function
            year=Coalesce(
                Cast(
                    Substr('book_publish', 
                          Length('book_publish') - 4,  # Lấy 4 ký tự cuối
                          4),                          # Độ dài là 4
                    output_field=IntegerField()
                ),
                Value(0)  # Giá trị mặc định nếu không tìm thấy năm
            )
        ).order_by("-year")
    elif type == 3:
        from django.db.models import Avg, Count, Value
        from django.db.models.functions import Coalesce
        books = books.annotate(
            rateavg = Coalesce(Avg('rating__rating'),Value(0.0)),
            ratecount = Count('rating')
        ).order_by('-ratecount', '-rateavg')
    elif type == 4:
        from django.db.models import Avg, Count, Value
        from django.db.models.functions import Coalesce
        books = books.annotate(
            rateavg = Coalesce(Avg('rating__rating'),Value(0.0)),
            ratecount = Count('rating')
        ).order_by('-rateavg', '-ratecount')
    elif type == 6:
        # Sắp xếp theo thời gian tạo mới nhất
        books = books.order_by('-created_at')
    elif type == 7:
        # Sử dụng hàm get_trending_books đã sửa đổi, truyền vào books_queryset
        books = get_trending_books(days=7, limit=100, books_queryset=books)
    
    return books
    
import pickle
import os
from django.conf import settings

# Gợi ý lọc cộng tác dựa trên ngươif dùng
def get_recommendations(user_id, num_recommendations=10):
    try:
        # Xác định đường dẫn file mô hình
        models_dir = os.path.join(settings.BASE_DIR, 'models')
        model_path = os.path.join(models_dir, 'finetuned_svd_model.pkl')
        if not os.path.exists(model_path):
            model_path = os.path.join(models_dir, 'pretrain_svd_model.pkl')
            if not os.path.exists(model_path):
                print("Không tìm thấy mô hình để tạo gợi ý")
                return []

        # Tải mô hình
        with open(model_path, 'rb') as f:
            loaded_data = pickle.load(f)
        
        # Kiểm tra định dạng file
        if isinstance(loaded_data, dict) and 'model' in loaded_data:
            model = loaded_data['model']
        else:
            model = loaded_data
            print("Đã tải trực tiếp đối tượng SVD (định dạng cũ)")

        # Lấy tất cả sách trong hệ thống
        from .models import Book, Rating
        all_books = Book.objects.all()
        user_rated_books = set(Rating.objects.filter(user_id=user_id).values_list('book_id', flat=True))

        # Dự đoán điểm số cho các sách chưa được đánh giá
        predictions = []
        for book in all_books:
            if book.book_id not in user_rated_books:
                # Dự đoán điểm số bằng SVD
                pred = model.predict(str(user_id), str(book.book_id))
                predictions.append((book, pred.est))

        # Sắp xếp theo điểm dự đoán giảm dần và lấy top N
        predictions.sort(key=lambda x: x[1], reverse=True)
        recommended_books = [pred[0] for pred in predictions[:num_recommendations]]
        
        return recommended_books

    except Exception as e:
        print(f"Lỗi khi tạo gợi ý cho user {user_id}: {e}")
        return []

from django.core.cache import cache
from .content_based_recommender import ContentBasedRecommender
import logging

logger = logging.getLogger(__name__)

def get_content_based_recommendations(book_id, n_recommendations=5):
    """Get recommendations với caching"""
    try:
        recommender = ContentBasedRecommender()
        return recommender.get_recommendations(book_id, n_recommendations)
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        return []

def update_recommendation_model():
    """Update model với cache invalidation"""
    try:
        recommender = ContentBasedRecommender()
        return recommender.update_recommendations()
    except Exception as e:
        logger.error(f"Error updating model: {str(e)}")
        return False

def get_trending_books(days=7, limit=10, books_queryset=None):
    from django.db.models import Count, F, ExpressionWrapper, FloatField, Q, Case, When, Value
    from django.db.models.functions import Coalesce
    from django.utils import timezone
    from .models import Book
    import datetime
    
    # Xác định thời điểm bắt đầu tính "gần đây"
    recent_date = timezone.now() - datetime.timedelta(days=days)
    
    # Sử dụng books_queryset nếu được cung cấp, nếu không thì lấy tất cả sách
    if books_queryset is None:
        base_queryset = Book.objects.all()
    else:
        base_queryset = books_queryset
    
    # Lấy danh sách sách và tính điểm thịnh hành
    trending_books = base_queryset.annotate(
        # Số lượng đánh giá gần đây
        recent_ratings=Count(
            'rating',
            filter=Q(rating__created_at__gte=recent_date)
        ),
        
        # Số lượng bình luận/đánh giá gần đây
        recent_reviews=Count(
            'reviews',
            filter=Q(reviews__created_at__gte=recent_date)
        ),
        
        # Số lượt xem gần đây (nếu có BookViewHistory)
        recent_views=Count(
            'bookviewhistory',
            filter=Q(bookviewhistory__viewed_at__gte=recent_date)
        ),
        
        # Tính điểm thịnh hành
        trending_score=ExpressionWrapper(
            # Lượt xem gần đây * 0.5
            (F('recent_views') * 0.5) +
            
            # Số lượng đánh giá gần đây * 30
            (F('recent_ratings') * 30) +
            
            # Số lượng bình luận gần đây * 20
            (F('recent_reviews') * 20) +
            
            # Bonus cho sách được cập nhật gần đây
            Case(
                When(updated_at__gte=recent_date, then=Value(50)),
                default=Value(0),
                output_field=FloatField()
            ),
            output_field=FloatField()
        )
    ).order_by('-trending_score')[:limit]
    
    return trending_books
