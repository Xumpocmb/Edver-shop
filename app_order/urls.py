from django.urls import path
from . import views

app_name = 'app_order'

urlpatterns = [
    path('pay/<int:order_id>/', views.payment_create, name='payment_create'),
    path('status/<int:order_id>/', views.payment_check_status, name='payment_check_status'),
    path('check/<int:order_id>/', views.payment_status_page, name='payment_status_page'),
    path('callback/', views.payment_callback, name='payment_callback'),
]