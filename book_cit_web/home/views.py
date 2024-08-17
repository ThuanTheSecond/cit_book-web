from django.shortcuts import render
from .models import Book, Rating
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.template import loader

def checkRate(userid = None, bookid = None):
    rate = Rating.objects.filter(user_id = userid, book_id = bookid).first()
    if rate:
        return rate
    return 0

def rateBook(userid, bookid, point):
    rate = checkRate(userid=userid, bookid=bookid)
    if not rate:
        rate1 = Rating(user_id=userid, book_id = bookid, rating = point)
        rate1.save()
        return
    rate.rating = point
    rate.save()

# def search(request):
#     if request.POST == 'POST':
#         sdata = {}
#         if 'sbutton' in request.POST:
#             print('hello')
#             match request.POST.get('stype'):
#                 case 0: #case title
                    
        
# Create your views here.
def index(request):
    bookList = {}
    bookList['popular'] = Book.objects.order_by('book_view')[0:10]  
    bookList['topVn'] = Book.objects.filter(book_lang = 'Vietnamese').order_by('book_view')[0:10]
    bookList['topFL'] = Book.objects.filter(book_lang = 'Foreign').order_by('book_view')[0:10]
    
    
    context = {
        'bookList' : bookList
    }
    template = loader.get_template('index.html')
    return HttpResponse(template.render(context, request))
    