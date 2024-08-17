from django.shortcuts import render
from .models import Book
from django.http import HttpResponse
from django.template import loader

# Create your views here.
def index(request):
    books = Book.objects.all()
    context = {
        'books': books,
    }
    template = loader.get_template('index.html')
    return HttpResponse(template.render(context, request))
    
def login(request):
    books = Book.objects.all()
    context = {
        'books': books,
    }
    template = loader.get_template('login.html')
    return HttpResponse(template.render(context, request))

def register(request):
    books = Book.objects.all()
    context = {
        'books': books,
    }
    template = loader.get_template('register.html')
    return HttpResponse(template.render(context, request))