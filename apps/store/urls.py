from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.ProductListView.as_view(), name='product_list'),
]
