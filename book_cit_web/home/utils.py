from django.http import HttpResponseRedirect
def normalize_vietnamese(text):
    import unicodedata
    text = unicodedata.normalize('NFKD', text)
    rawText =  ''.join(c for c in text if not unicodedata.combining(c))
    rawText = rawText.replace('đ','d').replace('Đ', 'D')
    return rawText

def pagePaginator(request, books):
    from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
    paginator = Paginator(books, 7)
    
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

# Thêm mới record vào ContentBook
def createBookContent():
    from home.models import ContentBook, Book, Book_Topic
    
    latest_book = Book.objects.latest('created_at')
    content = latest_book.book_title
    content = str(content)
    #  take topics of just insert book's topics
    # sai 
    topics = Book_Topic.objects.filter(book_id_id=latest_book.book_id).select_related('topic_id')
    for topic in topics:
        content +=f" {topic.topic_id.topic_name}"
        print(content) 
    content += f" {latest_book.book_author}"
    # insert new Content Book 
    newContent = ContentBook.objects.create(book = latest_book, content = content)
    print(newContent.content)

# Cập nhật nội dung trong table ContentBook
def updateBookContent():
    from home.models import ContentBook, Book, Book_Topic
    
    lasted_update = Book.objects.latest('updated_at')

    content = lasted_update.book_title
    content = str(content)
    
    topics = Book_Topic.objects.filter(book_id_id = lasted_update.book_id).select_related('topic_id')
    for topic in topics:
        content+=' '+ str(topic.topic_id.topic_name)
        print(content)
        
    content += f" {lasted_update.book_author}"
    content_update = ContentBook.objects.get(book_id = lasted_update.book_id)
    content_update.content = content
    content_update.save()

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
        books = books.order_by('book_view')
    if type == 2:
        from django.db.models import IntegerField
        from django.db.models.functions import Cast,  Substr, Length
        books = books.annotate(
                year = Cast(Substr('book_publish', Length('book_publish') - 3),output_field=IntegerField())
        ).order_by("-year")
    if type == 3:
        from django.db.models import Count, Avg
        books = books.annotate(
            ratecount = Count('rating')
        ).order_by('-ratecount')
    if type == 4:
        from django.db.models import Avg
        books = books.annotate(
        ratecount = Avg('rating__rating')
    ).order_by('ratecount')
    return books
    
