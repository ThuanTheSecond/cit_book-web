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
    verbose_name = 'Chủ đề'
    verbose_name_plural = 'Các chủ đề'
    extra = 1
    
    
    class Media:
        js = ('js/dynamic_topics.js',)
        css = {
            'all': ('css/admin_custom.css',)
        }
    
    def get_formset(self, request, obj=None, **kwargs):
        """Tùy chỉnh formset để validate dữ liệu"""
        formset = super().get_formset(request, obj, **kwargs)
        
        # Override clean method để thêm validation
        def clean(self):
            cleaned_data = super(formset.form, self).clean()
            if not cleaned_data.get('DELETE', False):  # Chỉ validate nếu form không bị đánh dấu xóa
                if not cleaned_data.get('topic_id'):
                    raise forms.ValidationError('Vui lòng chọn chủ đề')
            return cleaned_data
            
        formset.form.clean = clean
        return formset

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    inlines = [Book_TopicInline]
    prepopulated_fields = {
        "book_slug": ("book_title",),
    }
    list_display = ('book_title', 'book_author', 'book_lang')
    search_fields = ('book_title', 'book_author')
    list_filter = ('book_lang', 'created_at')
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('book_title', 'book_author', 'book_position', 'book_MFN')
        }),
        ('Thông tin xuất bản', {
            'fields': ('book_publish', 'isbn_10', 'isbn_13')
        }),
        ('Phân loại', {
            'fields': ('book_lang',)  # Đã xóa 'topic' khỏi đây
        }),
        ('Thông tin khác', {
            'fields': ('book_slug', 'bookImage', 'is_active')
        }),
    )

    class Media:
        js = ('admin/js/admin/RelatedObjectLookups.js', 'js/dynamic_topics.js')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not obj.book_slug:
            obj.book_slug = slugify(obj.book_title)
            obj.save()
            
    def save_related(self, request, form, formsets, change):
        """Xử lý lưu các quan hệ many-to-many và inline formsets"""
        for formset in formsets:
            # Kiểm tra xem có phải là Book_TopicInline formset không
            if isinstance(formset, Book_TopicInline):
                instances = formset.save(commit=False)
                
                # Xử lý các instance bị xóa
                for obj in formset.deleted_objects:
                    obj.delete()
                
                # Lưu các instance mới và cập nhật
                for instance in instances:
                    if not instance.pk:  # Nếu là instance mới
                        instance.book_id = form.instance
                    instance.save()
                
                # Đảm bảo tất cả các m2m relations được lưu
                formset.save_m2m()
            else:
                formset.save()
        
        # Lưu các quan hệ many-to-many khác
        form.save_m2m()

    def get_inline_instances(self, request, obj=None):
        """Đảm bảo inlines được load đúng cách"""
        if not obj:  # Nếu đang tạo mới object
            return []
        return super().get_inline_instances(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """Tùy chỉnh form"""
        form = super().get_form(request, obj, **kwargs)
        return form

    def response_change(self, request, obj):
        """Xử lý sau khi lưu thành công"""
        response = super().response_change(request, obj)
        if "_continue" not in request.POST:
            # Refresh lại object để đảm bảo dữ liệu mới nhất
            obj.refresh_from_db()
        return response

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
