from django.db import models
# from account.models import user
from django.db.models import Transform, CharField
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from .utils import createBookContent, updateContentRecommend, updateBookContent
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

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
    book_title = models.CharField(max_length=300)  # Đã ok
    book_author = models.CharField(max_length=250)  # Đã ok
    book_position = models.CharField(max_length=200)  # Tăng từ 100 lên 200
    book_MFN = models.PositiveIntegerField()
    book_slug = models.SlugField(blank=True, max_length=350)  # Tăng độ dài
    book_publish = models.CharField(max_length=200, default='No information', blank=True)
    topic = models.ManyToManyField(Topic, through="Book_Topic")
    book_view = models.PositiveIntegerField(default=0)
    book_lang = models.CharField(max_length=10, choices=Language.choices, default=Language.FL)
    bookImage = models.ImageField(upload_to='imgBooks\\', default='imgBooks\\nothumb.jpg')
    isbn_10 = models.CharField(max_length=15, blank=True)
    isbn_13 = models.CharField(max_length=15, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Đã ok
    
    def __str__(self):
        # Handle case when book_id is None (new book not saved yet)
        display_id = (self.book_id - 3000) if self.book_id is not None else "NEW"
        
        # Handle potential None values in other fields
        title = self.book_title or "Untitled"
        author = self.book_author or "Unknown"
        publish = self.book_publish or "No info"
        position = self.book_position or "Unknown"
        mfn = self.book_MFN or "Unknown"
        
        return f'{display_id}-{title},{author},{publish},{position},{mfn},{self.is_active}' 
    
class Book_Topic(models.Model):
    book_id = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='book_topics')
    topic_id = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='topic_books')
    
    class Meta:
        unique_together = ('book_id', 'topic_id')
        verbose_name = 'Chủ đề sách'
        verbose_name_plural = 'Các chủ đề sách'

    def __str__(self):
        return f"{self.book_id.book_title} - {self.topic_id.topic_name}"

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
    content = models.CharField(max_length= 700)

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
    rating = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], blank=True, null=True)  # Thêm null=True
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'book']

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

# Dùng để thêm extension Unaccent của postgresql
class Unaccent(Transform):
    lookup_name = 'unaccent'
    function = 'unaccent'
    output_field = CharField()
CharField.register_lookup(Unaccent)

# Signal handlers
from django.db import transaction

# Global set to track books being deleted
_books_being_deleted = set()

@receiver(pre_delete, sender=Book)
def cleanup_book_related_data_before_delete(sender, instance, **kwargs):
    """Set flag to prevent content updates during deletion"""
    try:
        book_id = instance.book_id
        logger.info(f'Starting cleanup for book: {instance.book_title} (ID: {book_id})')
        
        # Add to global deletion set
        _books_being_deleted.add(book_id)
        
        # Don't manually delete CASCADE relationships - let Django handle them
        # Just log what will be deleted
        content_books_count = ContentBook.objects.filter(book=instance).count()
        ratings_count = Rating.objects.filter(book=instance).count()
        comments_count = Comment.objects.filter(book=instance).count()
        favlist_count = FavList.objects.filter(book=instance).count()
        toreads_count = ToReads.objects.filter(book=instance).count()
        amazon_ratings_count = AmazonRating.objects.filter(book=instance).count()
        view_history_count = BookViewHistory.objects.filter(book=instance).count()
        reviews_count = BookReview.objects.filter(book=instance).count()
        book_topics_count = Book_Topic.objects.filter(book_id=instance).count()
        
        logger.info(f'Book deletion will cascade to: {content_books_count} ContentBook, {ratings_count} Rating, {comments_count} Comment, {favlist_count} FavList, {toreads_count} ToReads, {amazon_ratings_count} AmazonRating, {view_history_count} BookViewHistory, {reviews_count} BookReview, {book_topics_count} Book_Topic records')
        
    except Exception as e:
        logger.error(f'Error in pre_delete handler for book {instance.book_title}: {str(e)}')
        # Don't re-raise - allow deletion to continue

@receiver(post_delete, sender=Book)
def cleanup_deletion_flag(sender, instance, **kwargs):
    """Clean up the deletion flag after book is deleted"""
    try:
        book_id = instance.book_id
        if book_id in _books_being_deleted:
            _books_being_deleted.remove(book_id)
            logger.info(f'Removed deletion flag for book ID: {book_id}')
    except Exception as e:
        logger.error(f'Error cleaning up deletion flag: {str(e)}')

@receiver(post_save, sender=Book)
def createBookContent_signal(sender, instance, created, **kwargs):
    try:
        # Skip if the book is being deleted or doesn't have a valid pk
        if not instance.pk or not instance.is_active:
            return
            
        # Skip if this book is being deleted
        if instance.book_id in _books_being_deleted:
            logger.info(f'Book {instance.book_title} is being deleted, skipping content creation')
            return
            
        if created:
            content = createBookContent(instance)
        else:
            content = updateBookContent(instance)
            
        # Retrain model sau khi thêm/cập nhật sách
        from .content_based_recommender import ContentBasedRecommender
        recommender = ContentBasedRecommender()
        recommender.train_model()
        
    except Exception as e:
        logger.error(f'Error in Book signal handler for {instance.book_title}: {str(e)}')

@receiver([post_save, post_delete], sender=Book_Topic)
def update_content_on_topic_change(sender, instance, **kwargs):
    try:
        book = instance.book_id
        
        # Skip if the book is being deleted or doesn't exist
        if not book or not book.pk:
            logger.info('Book reference is None or has no pk, skipping content update')
            return
        
        # Skip if this book is being deleted
        if book.book_id in _books_being_deleted:
            logger.info(f'Book {book.book_title} is being deleted, skipping content update')
            return
        
        # Check if the book still exists in the database before proceeding
        try:
            book.refresh_from_db()
        except Book.DoesNotExist:
            logger.info(f'Book {book.pk} no longer exists, skipping content update')
            return
        
        # Additional check: verify the book is still active
        if not book.is_active:
            logger.info(f'Book {book.pk} is not active, skipping content update')
            return
            
        # Only proceed if book definitely exists and is active
        content = updateBookContent(book)
        logger.info(f'Successfully updated content for book: {book.book_title}')
        
        # Retrain model sau khi cập nhật topic
        from .content_based_recommender import ContentBasedRecommender
        recommender = ContentBasedRecommender()
        recommender.train_model()
        
    except Book.DoesNotExist:
        logger.info(f'Book was deleted during signal processing, skipping content update')
    except Exception as e:
        logger.error(f'Error in Book_Topic signal handler: {str(e)}')



