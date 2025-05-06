from django.urls import path
from . import views
from .admin import admin_site

urlpatterns = [
    path('', views.index, name='index'),
    path('modern/', views.index_modern, name='index_modern'),
    path('searchSlug', views.searchSlug, name='search_slug'),
    path('book/detail/id=<int:id>', views.bookDetail, name='book_detail'), 
    path('category/filter/id=<int:id>', views.categoryFilter, name='category'),
    path('search/<str:search_type>/<int:ftype>/<str:query>', views.search, name='search'),  
    path('searchAdvance/', views.searchAdvance, name='searchAdvance'),  
    path('categoryFilter/<str:cid>/<int:type>', views.categoryFilter, name='categoryFilter'), 
    path('topicFilter/<str:tid>/<int:type>', views.topicFilter, name='topicFilter'), 
    path('mybook/', views.myBook, name='myBook'),
    path('test', views.test, name='test'),  
    path('history/', views.view_history, name='view_history'),
    path('profile/', views.profile, name='profile'),
    path('book/review/<int:book_id>', views.add_review, name='add_review'),
]

htmxpatterns = [
    path('search_post/', views.searchPost, name='search_post'),
    path('category_post/', views.categoryPost, name='category_post'),
    path('rating_post/', views.ratingPost, name='rating_post'),
    path('ratingCheck_post/', views.ratingCheckPost, name='ratingCheck_post'),
    path('clear_rating_post/', views.clearRatingPost, name='clear_rating_post'),
    path('wishList_post/', views.wishListPost, name='wishList_post'),
    path('wishCheck_post/', views.wishCheckPost, name='wishCheck_post'),
    path('searchType_post/', views.searchTypePost, name='searchType_post'),
    path('topicList_post/', views.topicListPost, name='topicList_post'),
]
urlpatterns+= htmxpatterns