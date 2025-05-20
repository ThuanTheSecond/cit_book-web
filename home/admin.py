from django.contrib import admin
from django.utils.text import slugify
from django.utils.html import format_html
from django.urls import path, reverse
from django import forms
from .models import Book, Topic, Book_Topic, Rating, ToReads, BookViewHistory, AuthorViewHistory, FavList
from django.db.models import Count
from django.utils import timezone
from . import stats


# Register your models here.
@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    prepopulated_fields = {
        "topic_slug": ("topic_name",),
    }
    list_display = ('topic_name', 'get_book_count', 'actions_column')
    search_fields = ('topic_name',)
    actions = ['delete_selected_topics']
    
    def get_book_count(self, obj):
        return Book_Topic.objects.filter(topic_id=obj).count()
    get_book_count.short_description = 'Số sách'
    
    def actions_column(self, obj):
        return format_html(
            '<a class="button" href="{}">Sửa</a> '
            '<a class="button" style="background-color: #dc3545;" href="{}">Xóa</a>',
            reverse('admin:home_topic_change', args=[obj.pk]),
            reverse('admin:home_topic_delete', args=[obj.pk])
        )
    actions_column.short_description = 'Thao tác'
    
    def delete_selected_topics(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'Đã xóa {count} chủ đề.')
    delete_selected_topics.short_description = "Xóa các chủ đề đã chọn"

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
    list_display = ('book_title', 'book_author', 'book_lang', 'get_topics', 'actions_column')
    search_fields = ('book_title', 'book_author')
    list_filter = ('book_lang', 'created_at')
    actions = ['delete_selected_books']
    
    def get_topics(self, obj):
        topics = Book_Topic.objects.filter(book_id=obj).values_list('topic_id__topic_name', flat=True)
        return ", ".join(topics)
    get_topics.short_description = 'Chủ đề'
    
    def actions_column(self, obj):
        return format_html(
            '<a class="button" href="{}">Sửa</a> '
            '<a class="button" style="background-color: #dc3545;" href="{}">Xóa</a>',
            reverse('admin:home_book_change', args=[obj.pk]),
            reverse('admin:home_book_delete', args=[obj.pk])
        )
    actions_column.short_description = 'Thao tác'
    
    def delete_selected_books(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'Đã xóa {count} sách.')
    delete_selected_books.short_description = "Xóa các sách đã chọn"
    
    class Media:
        js = ('admin/js/admin/RelatedObjectLookups.js', 'js/dynamic_topics.js')
        css = {
            'all': ('css/admin_custom.css',)
        }

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
                        # Sử dụng update_or_create để tránh lỗi trùng lặp
                        Book_Topic.objects.update_or_create(
                            book_id=form.instance,
                            topic_id=instance.topic_id,
                            defaults={}
                        )
                    else:
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
