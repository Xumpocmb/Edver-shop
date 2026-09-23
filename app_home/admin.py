from django.contrib import admin
from django.utils.html import format_html
from django_summernote.admin import SummernoteModelAdmin
from .models import Advantage, CartIcon, FooterInfo, Instagram, PhoneNumber, ProfileIcon, SiteFavicon, SiteLogo, SiteReview, StaticPage, TikTok


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


@admin.register(SiteFavicon)
class SiteFaviconAdmin(admin.ModelAdmin):
    list_display = ('id', 'favicon_preview')
    fields = ('image', 'favicon_preview')
    readonly_fields = ('favicon_preview',)

    def favicon_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 40px;" />', obj.image.url)
        return '-'

    favicon_preview.short_description = 'Предпросмотр'


@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
    list_display = ('id', 'number',)


@admin.register(Instagram)
class InstagramAdmin(admin.ModelAdmin):
    list_display = ('id', 'url', 'icon', 'icon_preview')

    def icon_preview(self, obj):
        if obj.icon_image:
            return format_html('<img src="{}" style="max-height: 32px;" />', obj.icon_image.url)
        return obj.icon or '-'

    icon_preview.short_description = 'Иконка'


@admin.register(ProfileIcon)
class ProfileIconAdmin(admin.ModelAdmin):
    list_display = ('id', 'icon', 'icon_preview')

    def icon_preview(self, obj):
        if obj.icon_image:
            return format_html('<img src="{}" style="max-height: 32px;" />', obj.icon_image.url)
        return obj.icon or '-'

    icon_preview.short_description = 'Иконка'


@admin.register(CartIcon)
class CartIconAdmin(admin.ModelAdmin):
    list_display = ('id', 'icon', 'icon_preview')

    def icon_preview(self, obj):
        if obj.icon_image:
            return format_html('<img src="{}" style="max-height: 32px;" />', obj.icon_image.url)
        return obj.icon or '-'

    icon_preview.short_description = 'Иконка'


@admin.register(TikTok)
class TikTokAdmin(admin.ModelAdmin):
    list_display = ('id', 'url',)


@admin.register(FooterInfo)
class FooterInfoAdmin(admin.ModelAdmin):
    list_display = ('id', 'text')


@admin.register(Advantage)
class AdvantageAdmin(admin.ModelAdmin):
    list_display = ('icon', 'title', 'order', 'is_active')
    list_display_links = ('title',)
    list_editable = ('order', 'is_active')
    list_filter = ('is_active',)
    ordering = ('order', 'id')


@admin.register(SiteReview)
class SiteReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'rating', 'is_published', 'created_at')
    list_filter = ('is_published', 'rating')
    list_editable = ('is_published',)


@admin.register(StaticPage)
class StaticPageAdmin(SummernoteModelAdmin):
    summernote_fields = ('content',)
    list_display = ('title', 'slug', 'is_published', 'updated_at')
    list_filter = ('is_published',)
    list_editable = ('is_published',)
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'content')

    class Media:
        css = {'all': ('css/admin.css',)}
