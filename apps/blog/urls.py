from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.PostListView.as_view(), name='post_list'),
    path('write/', views.PostCreateView.as_view(), name='post_create'),
    path('my-posts/', views.MyPostsView.as_view(), name='my_posts'),
    path('category/<slug:slug>/',
         views.CategoryListView.as_view(), name='category_posts'),
    path('tag/<slug:slug>/', views.TagListView.as_view(), name='tag_posts'),
    path('post/<slug:slug>/', views.PostDetailView.as_view(), name='post_detail'),
    path('post/<slug:slug>/edit/', views.PostUpdateView.as_view(), name='post_edit'),
    path('post/<slug:slug>/delete/',
         views.PostDeleteView.as_view(), name='post_delete'),
    path('post/<slug:slug>/comment/', views.add_comment, name='add_comment'),
    # Admin-only: Create SEO blog posts
    path('admin/create-seo-posts/', views.create_seo_posts, name='create_seo_posts'),
]
