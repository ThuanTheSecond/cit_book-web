import unicodedata
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponseRedirect
from sklearn.metrics.pairwise import linear_kernel



def normalize_vietnamese(text):
    text = unicodedata.normalize('NFKD', text)
    rawText =  ''.join(c for c in text if not unicodedata.combining(c))
    rawText = rawText.replace('đ','d').replace('Đ', 'D')
    return rawText

def pagePaginator(request, books):
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

def createBookContent():
    from home.models import ContentBook, Book, Book_Topic
    import pandas as pd
    latest_book = Book.objects.latest('created_at')
    content = latest_book.book_title
    content = str(content)
    #  take topics of just insert book's topics
    # sai 
    topics = Book_Topic.objects.filter(book_id_id=latest_book.book_id).select_related('topic_id')
    for topic in topics:
        content +=' '+ str(topic.topic_id.topic_name)
        print(content) 
      
    # insert new Content Book 
    newContent = ContentBook(book = latest_book, content = content)
    newContent.save()

def updateBookContent():
    from home.models import ContentBook, Book, Book_Topic
    import pandas as pd
    lasted_update = Book.objects.latest('updated_at')

    content = lasted_update.book_title
    content = str(content)
    topics = Book_Topic.objects.filter(book_id_id = lasted_update.book_id).select_related('topic_id')
    for topic in topics:
        content+=' '+ str(topic.topic_id.topic_name)
        print(content)
    content_update = ContentBook.objects.get(book_id = lasted_update.book_id)
    content_update.content = content
    content_update.save()

    # updateContentDic = {
    #     'book_id': lasted_update.book_id,
    #     'content': content
    # }
    # updateContent_df = pd.DataFrame(updateContentDic, index=[0])
    # return updateContent_df
    
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

    # newContent_df['content'] = newContent_df['content'].fillna('')
    # newContent_df['content'] = newContent_df['content'].astype(str)

    # Vector hóa nội dung sách mới
    book_content_matrix = book_tfidf.fit_transform(book_df['content']) 
    # newContent_matrix = book_tfidf.transform(newContent_df['content'])

    # Gộp ma trận nội dung sách cũ và mới lại
    # updatedContent_matrix = vstack([book_content_matrix, newContent_matrix])
        
    # Cập nhật ma trận cosine similarity cho toàn bộ hệ thống
    cosine_similarity = linear_kernel(book_content_matrix, book_content_matrix)


    # Lưu TF-IDF Vectorizer
    with open('./home/recommend/book_tfidf_vectorizer.pkl', 'wb') as f:
        pickle.dump(book_tfidf, f)

    with open('./home/recommend/book_cosine_similarity.pkl', 'wb') as f:
        pickle.dump(cosine_similarity, f)
    print('updated content after delete')

def getRecommend_content(book_id):
    from home.models import ContentBook
    import pickle
    import pandas as pd
    
    bookContents = ContentBook.objects.all().order_by('book_id').values('book_id')
    book_df = pd.DataFrame(bookContents)
    # Thao tac de truy xuat index cua book_id trong dataframe book_df
    book_df.set_index('book_id', inplace=True)
    book_index = book_df.index.get_loc(book_id)
    
    # lay ham cosine_similartity ra de tinh toan goi y voi tham so la index cua book_id
    with open('./home/recommend/book_cosine_similarity.pkl', 'rb') as f:
        cosine_similarity = pickle.load(f)
    choice = book_index
    similarity_scores = list(enumerate(cosine_similarity[choice]))
    similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)
    similarity_scores = similarity_scores[1:6]

    # Get the similar books index
    books_index = [i[0] for i in similarity_scores]
    books_index_real = []
    for i in books_index:
        books_index_real.append(i+3000) 
    return books_index_real
    

    
