from django.urls import path

from app_order import views as order_views
from . import views

app_name = 'app_user'

urlpatterns = [
    path('', views.profile_dashboard, name='profile'),
    path('orders/', order_views.orders_list, name='orders_list'),
    path('orders/<int:order_id>/', order_views.order_detail, name='order_detail'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
]