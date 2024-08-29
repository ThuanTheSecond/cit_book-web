from django.db import models
# from account.models import user
from django.db.models import Transform, CharField
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator

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
    is_active = models.BooleanField(default= True)
    
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

# Dùng để thêm extension Unaccent của postgresql
class Unaccent(Transform):
    lookup_name = 'unaccent'
    function = 'unaccent'

CharField.register_lookup(Unaccent)