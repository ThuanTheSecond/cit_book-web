from django.contrib import admin
from .models import Book, Topic, Book_Topic

# Register your models here.
admin.site.register(Book_Topic)

class TopicInline(admin.TabularInline):
    model = Book.topic.through

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    prepopulated_fields ={
        "topic_slug": ("topic_name",),
    }

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    prepopulated_fields ={
        "book_slug": ("book_MFN",),
    }
    inlines = [TopicInline]