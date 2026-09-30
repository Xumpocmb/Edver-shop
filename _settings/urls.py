from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app_home.urls')),
    path('catalog/', include('app_catalog.urls')),
    path('cart/', include('app_cart.urls')),
    path('profile/', include('app_user.urls')),
    path('orders/', include('app_order.urls')),
    path('summernote/', include('django_summernote.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = 'app_home.error_views.permission_denied'
handler404 = 'app_home.error_views.page_not_found'
handler500 = 'app_home.error_views.server_error'
