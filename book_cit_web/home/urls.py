from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('test/', views.searchTest, name='search_test'),
    path('book/detail/id=<int:id>', views.bookDetail, name='book_detail'), 
    path('category/<str:name>', views.category, name='category'),
    path('search/<str:name>', views.search, name='search'),  
]

htmxpatterns = [
    path('search_post/', views.searchPost, name='search_post'),
]
urlpatterns+= htmxpatterns