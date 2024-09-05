from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('searchSlug', views.searchSlug, name='search_slug'),
    path('book/detail/id=<int:id>', views.bookDetail, name='book_detail'), 
    path('category/filter/id=<int:id>', views.categoryFilter, name='category'),
    path('search/<str:search_type>/<str:query>', views.search, name='search'),  
    path('test', views.test, name='test'),  
]

htmxpatterns = [
    path('search_post/', views.searchPost, name='search_post'),
    path('category_post/', views.categoryPost, name='category_post'),
    path('rating_post/', views.ratingPost, name='rating_post'),
    path('clear_rating_post/', views.clearRatingPost, name='clear_rating_post'),
    path('wishList_post/', views.wishListPost, name='wishList_post'),
    path('wishCheck_post/', views.wishCheckPost, name='wishCheck_post'),
    path('searchType_post/', views.searchTypePost, name='searchType_post'),
]
urlpatterns+= htmxpatterns