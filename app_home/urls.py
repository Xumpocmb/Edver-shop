from django.urls import path
from . import views

app_name = 'app_home'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contacts/', views.contacts, name='contacts'),
    path('reviews/', views.site_reviews, name='site_reviews'),
    path('privacy/', views.static_page, {'slug': 'privacy'}, name='privacy'),
    path('payment/', views.static_page, {'slug': 'payment'}, name='payment'),
    path('offer/', views.static_page, {'slug': 'offer'}, name='offer'),
]
