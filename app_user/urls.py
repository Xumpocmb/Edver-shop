from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

app_name = 'app_user'

urlpatterns = [
    # Профиль
    path('', views.profile_dashboard, name='profile'),
    path('edit/', views.profile_edit, name='profile_edit'),

    # Заказы
    path('orders/', views.profile_dashboard, name='orders_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/reorder/', views.reorder, name='reorder'),
    path('orders/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),

    # Пароль
    path('password/change/', views.UserPasswordChangeView.as_view(), name='password_change'),
    path('password/change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='app_user/password_change_done.html'), name='password_change_done'),

    # Django auth (password reset и др.)
    path('password/reset/', auth_views.PasswordResetView.as_view(template_name='app_user/password_reset.html'), name='password_reset'),
    path('password/reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='app_user/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='app_user/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='app_user/password_reset_complete.html'), name='password_reset_complete'),

    # Auth
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('register/', views.UserRegisterView.as_view(), name='register'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
]