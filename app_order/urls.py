from django.urls import path
from . import views

app_name = 'app_order'

urlpatterns = [
    # Заказы
    path('', views.orders_list, name='orders_list'),
    path('<int:order_id>/', views.order_detail, name='order_detail'),

    # Оплата
    path('<int:order_id>/pay/', views.payment_create, name='payment_create'),
    path('<int:order_id>/status/', views.payment_check_status, name='payment_check_status'),
    path('<int:order_id>/check/', views.payment_status_page, name='payment_status_page'),
    path('callback/', views.payment_callback, name='payment_callback'),
]