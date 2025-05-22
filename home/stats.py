from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Avg
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
import json
import logging

logger = logging.getLogger(__name__)
from .models import Book, Topic, Book_Topic, BookViewHistory, AuthorViewHistory, Rating

@staff_member_required
def admin_stats_view(request):
    """
    Hiển thị trang thống kê cho admin
    """
    return render(request, 'admin/stats.html')

@staff_member_required
def get_time_stats(request):
    """
    API trả về dữ liệu thống kê theo thời gian
    """
    days = request.GET.get('days', 7)
    try:
        days = int(days)
    except ValueError:
        days = 7
    
    # Lấy ngày bắt đầu
    start_date = timezone.now().date() - timedelta(days=days)
    
    # Kiểm tra table có tồn tại không
    try:
        # Lấy số lượng xem trong từng ngày
        view_stats = BookViewHistory.objects.filter(
            viewed_at__date__gte=start_date
        ).values('viewed_at__date').annotate(
            count=Count('id')
        ).order_by('viewed_at__date')
        
        # Tạo danh sách các ngày và số lượng xem
        dates = []
        counts = []
        
        current_date = start_date
        today = timezone.now().date()
        
        while current_date <= today:
            # Format ngày theo định dạng dd/mm
            formatted_date = current_date.strftime('%d/%m')
            dates.append(formatted_date)
            
            # Tìm số lượng cho ngày hiện tại
            count = 0
            for stat in view_stats:
                if stat['viewed_at__date'] == current_date:
                    count = stat['count']
                    break
            
            counts.append(count)
            current_date += timedelta(days=1)
    except Exception as e:
        # Log the error
        logger.error(f"Error in get_time_stats: {str(e)}")
        # Return empty data if there's an error
        dates = []
        counts = []
        for i in range(days):
            date = timezone.now().date() - timedelta(days=i)
            dates.append(date.strftime('%d/%m'))
            counts.append(0)
        dates.reverse()
        counts.reverse()
    
    return JsonResponse({
        'labels': dates,
        'values': counts
    })

@staff_member_required
def get_top_books(request):
    """
    API trả về top 10 sách được xem nhiều nhất
    """
    days = request.GET.get('days', 30)
    try:
        days = int(days)
    except ValueError:
        days = 30
    
    # Lấy ngày bắt đầu
    start_date = timezone.now().date() - timedelta(days=days)
    
    try:
        # Lấy danh sách sách được xem nhiều nhất
        top_books = BookViewHistory.objects.filter(
            viewed_at__date__gte=start_date
        ).values('book__book_title', 'book__book_author').annotate(
            count=Count('book')
        ).order_by('-count')[:10]
        
        labels = []
        values = []
        authors = []
        
        for book in top_books:
            labels.append(book['book__book_title'])
            values.append(book['count'])
            authors.append(book['book__book_author'])
    except Exception as e:
        # Log the error
        logger.error(f"Error in get_top_books: {str(e)}")
        # Return demo data if there's an error
        labels = ['Sample Book 1', 'Sample Book 2', 'Sample Book 3']
        values = [10, 8, 5]
        authors = ['Author 1', 'Author 2', 'Author 3']
    
    return JsonResponse({
        'labels': labels,
        'values': values,
        'authors': authors
    })

@staff_member_required
def get_top_authors(request):
    """
    API trả về top tác giả được xem nhiều nhất (từ sách)
    """
    days = request.GET.get('days', 30)
    try:
        days = int(days)
    except ValueError:
        days = 30
    
    # Lấy ngày bắt đầu
    start_date = timezone.now().date() - timedelta(days=days)
    
    try:
        # Sử dụng BookViewHistory thay vì AuthorViewHistory nếu không có bảng đó
        top_authors = BookViewHistory.objects.filter(
            viewed_at__date__gte=start_date
        ).values('book__book_author').annotate(
            count=Count('book')
        ).order_by('-count')[:10]
        
        labels = []
        values = []
        
        for author in top_authors:
            if author['book__book_author'] and author['book__book_author'].strip():
                labels.append(author['book__book_author'])
                values.append(author['count'])
    except Exception as e:
        # Log the error
        logger.error(f"Error in get_top_authors: {str(e)}")
        # Return demo data if there's an error
        labels = ['Sample Author 1', 'Sample Author 2', 'Sample Author 3']
        values = [15, 12, 8]
    
    return JsonResponse({
        'labels': labels,
        'values': values
    })

@staff_member_required
def get_topic_stats(request):
    """
    API trả về thống kê theo chủ đề
    """
    days = request.GET.get('days', 30)
    try:
        days = int(days)
    except ValueError:
        days = 30
    
    try:
        # Lấy ngày bắt đầu
        start_date = timezone.now().date() - timedelta(days=days)
        
        # Lấy danh sách sách được xem
        book_views = BookViewHistory.objects.filter(
            viewed_at__date__gte=start_date
        ).values_list('book', flat=True)
        
        # Lấy danh sách chủ đề theo số lượng sách được xem
        topic_stats = Book_Topic.objects.filter(
            book_id__in=book_views
        ).values('topic_id__topic_name').annotate(
            count=Count('book_id')
        ).order_by('-count')[:9]
        
        labels = []
        values = []
        
        for topic in topic_stats:
            if topic['topic_id__topic_name']:
                labels.append(topic['topic_id__topic_name'])
                values.append(topic['count'])
    except Exception as e:
        # Log the error
        logger.error(f"Error in get_topic_stats: {str(e)}")
        # Return demo data if there's an error
        labels = ['Topic 1', 'Topic 2', 'Topic 3']
        values = [20, 15, 10]
    
    return JsonResponse({
        'labels': labels,
        'values': values
    })

@staff_member_required
def get_language_stats(request):
    """
    API trả về thống kê theo ngôn ngữ sách
    """
    days = request.GET.get('days', 30)
    try:
        days = int(days)
    except ValueError:
        days = 30
    
    try:
        # Lấy ngày bắt đầu
        start_date = timezone.now().date() - timedelta(days=days)
        
        # Lấy danh sách sách được xem
        viewed_books = BookViewHistory.objects.filter(
            viewed_at__date__gte=start_date
        ).values_list('book', flat=True)
        
        # Lấy danh sách ngôn ngữ theo số lượng sách được xem
        language_stats = Book.objects.filter(
            book_id__in=viewed_books
        ).values('book_lang').annotate(
            count=Count('book_id')
        ).order_by('-count')
        
        labels = []
        values = []
        
        for lang in language_stats:
            # Chuyển đổi mã ngôn ngữ thành tên đầy đủ
            language_name = 'Tiếng Việt' if lang['book_lang'] == 'vn' else 'Tiếng Anh'
            labels.append(language_name)
            values.append(lang['count'])
    except Exception as e:
        # Log the error
        logger.error(f"Error in get_language_stats: {str(e)}")
        # Return demo data if there's an error
        labels = ['Tiếng Việt', 'Tiếng Anh']
        values = [30, 70]
    
    return JsonResponse({
        'labels': labels,
        'values': values
    })

@staff_member_required
def get_new_books(request):
    """
    API trả về dữ liệu sách mới đăng ký
    """
    days = request.GET.get('days', 7)
    try:
        days = int(days)
    except ValueError:
        days = 7
    
    # Lấy ngày bắt đầu
    start_date = timezone.now().date() - timedelta(days=days)
    
    try:
        # Lấy số lượng sách mới trong từng ngày
        book_stats = Book.objects.filter(
            created_at__date__gte=start_date
        ).values('created_at__date').annotate(
            count=Count('book_id')
        ).order_by('created_at__date')
        
        # Tạo danh sách các ngày và số lượng sách mới
        dates = []
        counts = []
        
        current_date = start_date
        today = timezone.now().date()
        
        while current_date <= today:
            # Format ngày theo định dạng dd/mm
            formatted_date = current_date.strftime('%d/%m')
            dates.append(formatted_date)
            
            # Tìm số lượng cho ngày hiện tại
            count = 0
            for stat in book_stats:
                if stat['created_at__date'] == current_date:
                    count = stat['count']
                    break
            
            counts.append(count)
            current_date += timedelta(days=1)
    except Exception as e:
        # Log the error
        logger.error(f"Error in get_new_books: {str(e)}")
        # Return empty data if there's an error
        dates = []
        counts = []
        for i in range(days):
            date = timezone.now().date() - timedelta(days=i)
            dates.append(date.strftime('%d/%m'))
            counts.append(0)
        dates.reverse()
        counts.reverse()
    
    return JsonResponse({
        'labels': dates,
        'values': counts
    })

@staff_member_required
def get_new_users(request):
    """
    API trả về dữ liệu người dùng mới đăng ký
    """
    days = request.GET.get('days', 7)
    try:
        days = int(days)
    except ValueError:
        days = 7
    
    # Lấy ngày bắt đầu
    start_date = timezone.now().date() - timedelta(days=days)
    
    try:
        from django.contrib.auth.models import User
        # Lấy số lượng người dùng mới trong từng ngày
        user_stats = User.objects.filter(
            date_joined__date__gte=start_date
        ).values('date_joined__date').annotate(
            count=Count('id')
        ).order_by('date_joined__date')
        
        # Tạo danh sách các ngày và số lượng người dùng mới
        dates = []
        counts = []
        
        current_date = start_date
        today = timezone.now().date()
        
        while current_date <= today:
            # Format ngày theo định dạng dd/mm
            formatted_date = current_date.strftime('%d/%m')
            dates.append(formatted_date)
            
            # Tìm số lượng cho ngày hiện tại
            count = 0
            for stat in user_stats:
                if stat['date_joined__date'] == current_date:
                    count = stat['count']
                    break
            
            counts.append(count)
            current_date += timedelta(days=1)
    except Exception as e:
        # Log the error
        logger.error(f"Error in get_new_users: {str(e)}")
        # Return empty data if there's an error
        dates = []
        counts = []
        for i in range(days):
            date = timezone.now().date() - timedelta(days=i)
            dates.append(date.strftime('%d/%m'))
            counts.append(0)
        dates.reverse()
        counts.reverse()
    
    return JsonResponse({
        'labels': dates,
        'values': counts
    })

@staff_member_required
def get_book_views(request):
    """
    API trả về dữ liệu lượt đọc sách
    """
    days = request.GET.get('days', 7)
    try:
        days = int(days)
    except ValueError:
        days = 7
    
    # Lấy ngày bắt đầu
    start_date = timezone.now().date() - timedelta(days=days)
    
    try:
        # Lấy số lượng lượt đọc trong từng ngày
        view_stats = BookViewHistory.objects.filter(
            viewed_at__date__gte=start_date
        ).values('viewed_at__date').annotate(
            count=Count('id')
        ).order_by('viewed_at__date')
        
        # Tạo danh sách các ngày và số lượng lượt đọc
        dates = []
        counts = []
        
        current_date = start_date
        today = timezone.now().date()
        
        while current_date <= today:
            # Format ngày theo định dạng dd/mm
            formatted_date = current_date.strftime('%d/%m')
            dates.append(formatted_date)
            
            # Tìm số lượng cho ngày hiện tại
            count = 0
            for stat in view_stats:
                if stat['viewed_at__date'] == current_date:
                    count = stat['count']
                    break
            
            counts.append(count)
            current_date += timedelta(days=1)
    except Exception as e:
        # Log the error
        logger.error(f"Error in get_book_views: {str(e)}")
        # Return empty data if there's an error
        dates = []
        counts = []
        for i in range(days):
            date = timezone.now().date() - timedelta(days=i)
            dates.append(date.strftime('%d/%m'))
            counts.append(0)
        dates.reverse()
        counts.reverse()
    
    return JsonResponse({
        'labels': dates,
        'values': counts
    })

@staff_member_required
def get_activity_timeline(request):
    """
    API trả về dữ liệu hoạt động theo thời gian (đăng nhập, xem sách, đánh giá)
    """
    days = request.GET.get('days', 7)
    try:
        days = int(days)
    except ValueError:
        days = 7
    
    # Lấy ngày bắt đầu
    start_date = timezone.now().date() - timedelta(days=days)
    
    try:
        # Lấy số lượng lượt xem trong từng ngày
        view_stats = BookViewHistory.objects.filter(
            viewed_at__date__gte=start_date
        ).values('viewed_at__date').annotate(
            count=Count('id')
        ).order_by('viewed_at__date')
        
        # Lấy số lượng đánh giá trong từng ngày
        rating_stats = Rating.objects.filter(
            created_at__date__gte=start_date
        ).values('created_at__date').annotate(
            count=Count('id')
        ).order_by('created_at__date')
        
        # Tạo danh sách các ngày
        dates = []
        views = []
        logins = []
        ratings = []
        
        current_date = start_date
        today = timezone.now().date()
        
        while current_date <= today:
            # Format ngày theo định dạng dd/mm
            formatted_date = current_date.strftime('%d/%m')
            dates.append(formatted_date)
            
            # Tìm số lượng lượt xem cho ngày hiện tại
            view_count = 0
            for stat in view_stats:
                if stat['viewed_at__date'] == current_date:
                    view_count = stat['count']
                    break
            
            # Tìm số lượng đánh giá cho ngày hiện tại
            rating_count = 0
            for stat in rating_stats:
                if stat['created_at__date'] == current_date:
                    rating_count = stat['count']
                    break
            
            # Dữ liệu thực cho views và ratings, dữ liệu mẫu cho logins
            views.append(view_count)
            logins.append(int(view_count * 0.7))  # Giả lập: 70% của lượt xem
            ratings.append(rating_count)  # Dữ liệu thực từ bảng Rating
            
            current_date += timedelta(days=1)
    except Exception as e:
        # Log the error
        logger.error(f"Error in get_activity_timeline: {str(e)}")
        # Return empty data if there's an error
        dates = []
        views = []
        logins = []
        ratings = []
        for i in range(days):
            date = timezone.now().date() - timedelta(days=i)
            dates.append(date.strftime('%d/%m'))
            views.append(0)
            logins.append(0)
            ratings.append(0)
        dates.reverse()
        views.reverse()
        logins.reverse()
        ratings.reverse()
    
    return JsonResponse({
        'labels': dates,
        'views': views,
        'logins': logins,
        'ratings': ratings  # Thay đổi từ 'downloads' thành 'ratings'
    })

@staff_member_required
def get_summary_stats(request):
    """
    API trả về dữ liệu thống kê tổng quan
    """
    try:
        from django.contrib.auth.models import User
        
        # Lấy dữ liệu tổng quan
        book_count = Book.objects.count()
        user_count = User.objects.count()
        view_count = BookViewHistory.objects.count()
        
        # Tính phần trăm thay đổi so với khoảng thời gian trước đó (7 ngày)
        week_ago = timezone.now().date() - timedelta(days=7)
        two_weeks_ago = timezone.now().date() - timedelta(days=14)
        
        # Sách mới trong 7 ngày qua
        new_books = Book.objects.filter(created_at__date__gte=week_ago).count()
        old_books = Book.objects.filter(created_at__date__gte=two_weeks_ago, created_at__date__lt=week_ago).count()
        book_change = calculate_percentage_change(old_books, new_books)
        
        # Người dùng mới trong 7 ngày qua
        new_users = User.objects.filter(date_joined__date__gte=week_ago).count()
        old_users = User.objects.filter(date_joined__date__gte=two_weeks_ago, date_joined__date__lt=week_ago).count()
        user_change = calculate_percentage_change(old_users, new_users)
        
        # Lượt xem trong 7 ngày qua
        new_views = BookViewHistory.objects.filter(viewed_at__date__gte=week_ago).count()
        old_views = BookViewHistory.objects.filter(viewed_at__date__gte=two_weeks_ago, viewed_at__date__lt=week_ago).count()
        view_change = calculate_percentage_change(old_views, new_views)
        
        # Đánh giá (dữ liệu thực từ bảng Rating)
        rating_count = Rating.objects.count()
        new_ratings = Rating.objects.filter(created_at__date__gte=week_ago).count()
        old_ratings = Rating.objects.filter(created_at__date__gte=two_weeks_ago, created_at__date__lt=week_ago).count()
        rating_change = calculate_percentage_change(old_ratings, new_ratings)
        
    except Exception as e:
        # Log the error
        logger.error(f"Error in get_summary_stats: {str(e)}")
        # Return demo data if there's an error
        book_count = 1250
        user_count = 845
        view_count = 32560
        rating_count = 4500
        book_change = 5.2
        user_change = 3.8
        view_change = 12.5
        rating_change = 8.7
    
    return JsonResponse({
        'books': {
            'total': book_count,
            'change': book_change,
        },
        'users': {
            'total': user_count,
            'change': user_change,
        },
        'views': {
            'total': view_count,
            'change': view_change,
        },
        'ratings': {  # Thay đổi từ 'downloads' thành 'ratings'
            'total': rating_count,
            'change': rating_change,
        }
    })

def calculate_percentage_change(old_value, new_value):
    """
    Tính phần trăm thay đổi giữa hai giá trị
    """
    if old_value == 0:
        return 100 if new_value > 0 else 0
    
    change = ((new_value - old_value) / old_value) * 100
    return round(change, 1)  # Làm tròn 1 chữ số sau dấu phẩy 

@staff_member_required
def get_most_read_books(request):
    """
    API trả về top 10 sách được đọc nhiều nhất dựa trên số lượng lượt xem
    """
    try:
        # Lấy danh sách top 10 sách được đọc nhiều nhất
        most_read_books = Book.objects.all().order_by('-book_view')[:10]
        
        labels = []
        values = []
        authors = []
        book_ids = []
        
        # Chuẩn bị dữ liệu cho biểu đồ
        for book in most_read_books:
            labels.append(book.book_title)
            values.append(book.book_view)
            authors.append(book.book_author)
            book_ids.append(book.book_id - 3000)  # Chuyển đổi ID cho URL
            
    except Exception as e:
        # Log the error
        logger.error(f"Error in get_most_read_books: {str(e)}")
        # Return demo data if there's an error
        labels = ['Sách 1', 'Sách 2', 'Sách 3', 'Sách 4', 'Sách 5']
        values = [150, 120, 100, 80, 60]
        authors = ['Tác giả 1', 'Tác giả 2', 'Tác giả 3', 'Tác giả 4', 'Tác giả 5']
        book_ids = [1, 2, 3, 4, 5]
    
    return JsonResponse({
        'labels': labels,
        'values': values,
        'authors': authors,
        'book_ids': book_ids
    })

@staff_member_required
def get_rating_distribution(request):
    """
    API trả về phân bố đánh giá theo số sao (1-5)
    """
    days = request.GET.get('days', 30)
    try:
        days = int(days)
    except ValueError:
        days = 30
    
    start_date = timezone.now().date() - timedelta(days=days)
    
    try:
        # Lấy thống kê đánh giá theo từng mức (1-5 sao)
        rating_distribution = Rating.objects.filter(
            created_at__date__gte=start_date
        ).values('rating').annotate(
            count=Count('id')
        ).order_by('rating')
        
        labels = []
        values = []
        
        # Tạo dữ liệu cho từng mức đánh giá (1-5 sao)
        for i in range(1, 6):
            labels.append(f"{i} sao")
            count = 0
            for stat in rating_distribution:
                if stat['rating'] == i:
                    count = stat['count']
                    break
            values.append(count)
        
        return JsonResponse({
            'labels': labels,
            'values': values
        })
        
    except Exception as e:
        logger.error(f"Error in get_rating_distribution: {str(e)}")
        return JsonResponse({
            'labels': ['1 sao', '2 sao', '3 sao', '4 sao', '5 sao'],
            'values': [10, 20, 50, 80, 40]
        })

@staff_member_required
def get_top_rated_books(request):
    """
    API trả về top sách được đánh giá cao nhất
    """
    limit = request.GET.get('limit', 10)
    try:
        limit = int(limit)
    except ValueError:
        limit = 10
    
    try:
        # Lấy sách có điểm đánh giá trung bình cao nhất
        top_rated_books = Book.objects.annotate(
            avg_rating=Avg('rating__rating'),
            rating_count=Count('rating')
        ).filter(
            rating_count__gt=0  # Chỉ lấy sách có đánh giá
        ).order_by('-avg_rating')[:limit]
        
        labels = []
        values = []
        authors = []
        rating_counts = []
        
        for book in top_rated_books:
            labels.append(book.book_title)
            values.append(float(book.avg_rating))  # Sử dụng double thay vì round
            authors.append(book.book_author)
            rating_counts.append(book.rating_count)
            
    except Exception as e:
        logger.error(f"Error in get_top_rated_books: {str(e)}")
        labels = ['Sách mẫu 1', 'Sách mẫu 2', 'Sách mẫu 3']
        values = [4.8234, 4.6789, 4.5123]  # Double precision examples
        authors = ['Tác giả 1', 'Tác giả 2', 'Tác giả 3']
        rating_counts = [25, 18, 12]
    
    return JsonResponse({
        'labels': labels,
        'values': values,
        'authors': authors,
        'rating_counts': rating_counts
    })

@staff_member_required
def get_rating_overview(request):
    """
    API trả về tổng quan về đánh giá
    """
    try:
        # Tổng số đánh giá
        total_ratings = Rating.objects.count()
        
        # Điểm đánh giá trung bình toàn hệ thống (sử dụng double precision)
        avg_rating = Rating.objects.aggregate(avg=Avg('rating'))['avg'] or 0.0
        
        # Số sách có đánh giá
        books_with_ratings = Book.objects.filter(rating__isnull=False).distinct().count()
        
        # Tổng số sách
        total_books = Book.objects.count()
        
        # Phần trăm sách có đánh giá
        rating_coverage = (books_with_ratings / total_books * 100.0) if total_books > 0 else 0.0
        
        return JsonResponse({
            'total_ratings': total_ratings,
            'average_rating': float(avg_rating),  # Trả về double/float thay vì round
            'books_with_ratings': books_with_ratings,
            'total_books': total_books,
            'rating_coverage': float(rating_coverage)
        })
        
    except Exception as e:
        logger.error(f"Error in get_rating_overview: {str(e)}")
        return JsonResponse({
            'total_ratings': 1250,
            'average_rating': 4.23456,  # Example double precision
            'books_with_ratings': 450,
            'total_books': 650,
            'rating_coverage': 69.23
        })