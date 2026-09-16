from django.urls import path
from . import views

app_name = 'app_cart'

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('add/', views.add_to_cart, name='add_to_cart'),
    path('item/<int:item_id>/update/', views.update_cart_item, name='update_cart_item'),
    path('item/<int:item_id>/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('clear/', views.clear_cart, name='clear_cart'),
    path('count/', views.cart_count, name='cart_count'),
]
