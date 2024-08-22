from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('searchSlug', views.searchSlug, name='search_slug'),
    path('book/detail/id=<int:id>', views.bookDetail, name='book_detail'), 
    path('category/filter/id=<int:id>', views.categoryFilter, name='category'),
    path('search/<str:skey>', views.search, name='search'),  
]

htmxpatterns = [
    path('search_post/', views.searchPost, name='search_post'),
    path('category_post/', views.categoryPost, name='category_post')
]
urlpatterns+= htmxpatterns