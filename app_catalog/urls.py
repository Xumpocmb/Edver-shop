from django.urls import path, re_path

from . import views

app_name = 'app_catalog'

SLUG_PATTERN = r'[\w\-]+'

urlpatterns = [
    path('', views.catalog_list, name='catalog_list'),
    path('search/', views.search_results, name='search_results'),
    re_path(r'^category/(?P<slug>' + SLUG_PATTERN + r')/$', views.category_detail, name='category_detail'),
    re_path(r'^product/(?P<slug>' + SLUG_PATTERN + r')/$', views.product_detail, name='product_detail'),
    re_path(r'^product/(?P<slug>' + SLUG_PATTERN + r')/review/$', views.add_review, name='add_review'),
]