from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.coming_soon, name='product_list'),  # Coming soon page for now
    # path('', views.ProductListView.as_view(), name='product_list'),  # Uncomment when ready
    # path('category/<slug:category_slug>/', views.ProductListView.as_view(), name='category_products'),
    # path('product/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
]