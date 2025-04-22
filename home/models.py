from django.db import models
# from account.models import user
from django.db.models import Transform, CharField
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .utils import createBookContent, updateContentRecommend, updateBookContent
from django.utils import timezone

# Create your models here.
class Topic(models.Model):
    topic_id= models.AutoField(primary_key=True)
    topic_name = models.CharField(max_length=100)
    topic_slug= models.SlugField()
    is_active = models.BooleanField(default= True)
    
    class META:
        verbose_name_plural = "Topics"
    def __str__(self):
        return f'{self.topic_name}'




class Book(models.Model):
    class Language(models.TextChoices):
        VN = 'Vietnamese'
        FL = 'Foreign'
    book_id = models.AutoField(primary_key=True)
    book_title = models.CharField(max_length=250)
    book_author = models.CharField(max_length=150)
    book_position = models.CharField(max_length= 100)
    book_MFN = models.PositiveIntegerField()
    book_slug = models.SlugField(blank=True)
    book_publish = models.CharField(max_length=100, default='No information', blank=True)
    topic = models.ManyToManyField(Topic, through= "Book_Topic")
    book_view = models.PositiveIntegerField(default=0)
    book_lang = models.CharField(max_length=10, choices=Language.choices, default=Language.FL)
    bookImage = models.ImageField(upload_to='imgBooks\\', default='imgBooks\\nothumb.jpg')
    isbn_10 = models.CharField(max_length=10, blank=True)
    isbn_13 = models.CharField(max_length=13, blank=True)
    is_active = models.BooleanField(default= True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'{self.book_id-3000}-{self.book_title},{self.book_author},{self.book_publish},{self.book_position},{self.book_MFN},{self.is_active}' 
    
class Book_Topic(models.Model):
    book_id = models.ForeignKey(Book, on_delete=models.CASCADE)
    topic_id = models.ForeignKey(Topic, on_delete=models.CASCADE)

class Rating(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(
        validators= [MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)

class Comment(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cmt = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)


class FavList(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
class ToReads(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

class ContentBook(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    content = models.CharField(max_length= 300)

class AmazonUser(models.Model):
    id = models.AutoField(primary_key=True)
    amazon_user_id = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'amazon_users'

    def __str__(self):
        return self.amazon_user_id

class AmazonRating(models.Model):
    id = models.AutoField(primary_key=True)
    amazon_user = models.ForeignKey(AmazonUser, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    rating = models.FloatField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    timestamp = models.DateTimeField()

    class Meta:
        db_table = 'amazon_ratings'
        unique_together = ('amazon_user', 'book')

    def __str__(self):
        return f'{self.amazon_user} rated {self.book} with {self.rating}'

# Dùng để thêm extension Unaccent của postgresql
class Unaccent(Transform):
    lookup_name = 'unaccent'
    function = 'unaccent'
    output_field = CharField()
CharField.register_lookup(Unaccent)

@receiver(post_save, sender=Book)
def createBookContent_signal(sender, instance, created, **kwargs):
    if created:
        createBookContent()
        print('create new book content')
    else:
        updateBookContent()
        print('update book content')
# tạo lịch sử xem sách :>>
class BookViewHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey('Book', on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-viewed_at']
        # Ensure one record per user-book combination
        unique_together = ['user', 'book']

    def __str__(self):
        return f"{self.user.username} viewed {self.book.book_title}"

class BookReview(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'book']  # Một user chỉ có thể review một lần cho mỗi sách

    def __str__(self):
        return f'{self.user.username} - {self.book.book_title} - {self.rating}★'

class AuthorViewHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    author = models.CharField(max_length=150)
    viewed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-viewed_at']
        unique_together = ['user', 'author']

    def __str__(self):
        return f"{self.user.username} viewed author {self.author}"

    
        
        