from django.contrib import admin
from django.utils.html import format_html
from .models import FooterInfo, Instagram, PhoneNumber, SiteLogo


@admin.register(SiteLogo)
class SiteLogoAdmin(admin.ModelAdmin):
    list_display = ('id', 'text', 'logo_preview')
    fields = ('text', 'image', 'logo_preview')
    readonly_fields = ('logo_preview',)

    def logo_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px;" />', obj.image.url)
        return '-'

    logo_preview.short_description = 'Предпросмотр'


@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
    list_display = ('id', 'number',)


@admin.register(Instagram)
class InstagramAdmin(admin.ModelAdmin):
    list_display = ('id', 'url',)


@admin.register(FooterInfo)
class FooterInfoAdmin(admin.ModelAdmin):
    list_display = ('id', 'text')
