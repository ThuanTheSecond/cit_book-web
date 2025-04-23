from django.contrib import admin
from django.utils.text import slugify
from .models import Book, Topic, Book_Topic, Rating, ToReads, BookViewHistory, AuthorViewHistory, FavList
from django.db.models import Count
from django.utils import timezone
from django.urls import path
from . import stats


# Register your models here.
@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    prepopulated_fields ={
        "topic_slug": ("topic_name",),
    }

class Book_TopicInline(admin.TabularInline):
    model = Book_Topic
    extra = 1  # Số lượng form trống để thêm mới

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    inlines = [Book_TopicInline]
    prepopulated_fields = {
        "book_slug": ("book_title",),
    }
    list_display = ('book_title', 'book_author', 'book_lang')
    search_fields = ('book_title', 'book_author')
    list_filter = ('book_lang', 'created_at')
    
    # Chỉ sử dụng fieldsets, không sử dụng fields
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('book_title', 'book_author', 'book_position', 'book_MFN')
        }),
        ('Thông tin xuất bản', {
            'fields': ('book_publish', 'isbn_10', 'isbn_13')
        }),
        ('Phân loại', {
            'fields': ('book_lang',)  # Bỏ trường topic ra khỏi đây
        }),
        ('Thông tin khác', {
            'fields': ('book_slug', 'bookImage', 'is_active')
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not obj.book_slug:
            obj.book_slug = slugify(obj.book_title)
            obj.save()

@admin.register(Book_Topic)
class Book_TopicAdmin(admin.ModelAdmin):
    list_display = ('book_id', 'topic_id')
    list_filter = ('topic_id',)
    search_fields = ('book_id__book_title', 'topic_id__topic_name')
    
@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'book__book_title')

@admin.register(ToReads)
class ToReadAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'book__book_title')

@admin.register(BookViewHistory)
class BookViewHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'viewed_at')
    list_filter = ('viewed_at',)
    search_fields = ('user__username', 'book__book_title')
    
@admin.register(AuthorViewHistory)
class AuthorViewHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'author', 'viewed_at')
    list_filter = ('viewed_at',)
    search_fields = ('user__username', 'author')

# Hàm để tùy chỉnh context của Admin Site
class CITLibraryAdminSite(admin.AdminSite):
    site_header = 'CIT LIBRARY Administration'
    site_title = 'CIT LIBRARY Admin'
    index_title = 'Library Management'
    
    def each_context(self, request):
        context = super().each_context(request)
        # Thêm số lượng thống kê vào context
        from django.contrib.auth.models import User
        context.update({
            'book_count': Book.objects.count(),
            'user_count': User.objects.count(),
            'topic_count': Topic.objects.count(),
            'new_today': BookViewHistory.objects.filter(viewed_at__date=timezone.now().date()).count(),
            'books_by_topic': dict(Book_Topic.objects.values_list('topic_id__topic_name').annotate(count=Count('book_id')).order_by('-count')[:5]),
        })
        return context
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('stats/', self.admin_view(stats.admin_stats_view), name='admin_stats'),
            path('api/stats/time/', self.admin_view(stats.get_time_stats), name='admin_time_stats'),
            path('api/stats/books/', self.admin_view(stats.get_top_books), name='admin_top_books'),
            path('api/stats/authors/', self.admin_view(stats.get_top_authors), name='admin_top_authors'),
            path('api/stats/topics/', self.admin_view(stats.get_topic_stats), name='admin_topic_stats'),
            path('api/stats/languages/', self.admin_view(stats.get_language_stats), name='admin_language_stats'),
            path('api/stats/new-books/', self.admin_view(stats.get_new_books), name='admin_new_books'),
            path('api/stats/new-users/', self.admin_view(stats.get_new_users), name='admin_new_users'),
            path('api/stats/book-views/', self.admin_view(stats.get_book_views), name='admin_book_views'),
            path('api/stats/popular-genres/', self.admin_view(stats.get_topic_stats), name='admin_popular_genres'),
            path('api/stats/activity-timeline/', self.admin_view(stats.get_activity_timeline), name='admin_activity_timeline'),
            path('api/stats/summary/', self.admin_view(stats.get_summary_stats), name='admin_summary_stats'),
            path('api/stats/most-read-books/', self.admin_view(stats.get_most_read_books), name='admin_most_read_books'),
        ]
        return custom_urls + urls

# Thay thế Admin Site mặc định với Admin Site tùy chỉnh
from django.contrib.admin import site

admin_site = CITLibraryAdminSite(name='admin')

# Re-register các model với Admin Site tùy chỉnh
admin_site.register(Book, BookAdmin)
admin_site.register(Topic, TopicAdmin)
admin_site.register(Book_Topic, Book_TopicAdmin)
admin_site.register(Rating, RatingAdmin)
admin_site.register(ToReads, ToReadAdmin)
admin_site.register(BookViewHistory, BookViewHistoryAdmin)
admin_site.register(AuthorViewHistory, AuthorViewHistoryAdmin)

# Đăng ký các model mặc định từ auth
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
admin_site.register(User, UserAdmin)
admin_site.register(Group, GroupAdmin)
