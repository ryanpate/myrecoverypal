from django.urls import path
from . import views
from .views import (
    PostListView, PostDetailView, PostCreateView, PostUpdateView,
    CategoryListView, TagListView, MyPostsView, add_comment
)

app_name = 'blog'

urlpatterns = [
    path('', PostListView.as_view(), name='post_list'),
    path('write/', PostCreateView.as_view(), name='post_create'),
    path('my-posts/', MyPostsView.as_view(), name='my_posts'),
    path('category/<slug:slug>/', CategoryListView.as_view(), name='category_posts'),
    path('tag/<slug:slug>/', TagListView.as_view(), name='tag_posts'),
    path('post/<slug:slug>/', PostDetailView.as_view(), name='post_detail'),
    path('post/<slug:slug>/edit/', PostUpdateView.as_view(), name='post_edit'),
    path('post/<slug:slug>/comment/', add_comment, name='add_comment'),
]
