from .models import (
    DEFAULT_BELPOCHTA_DELIVERY_NOTE,
    DEFAULT_COD_BELPOCHTA_NOTE,
    DEFAULT_COD_EVROPOCHTA_NOTE,
    DEFAULT_COD_PICKUP_NOTE,
    DEFAULT_ERIP_PAYMENT_NOTE,
    DEFAULT_EVROPOCHTA_DELIVERY_NOTE,
    DEFAULT_ONSITE_PAYMENT_NOTE,
    CartIcon,
    DeliveryInfo,
    FooterInfo,
    Instagram,
    OrderAvailability,
    PaymentInfo,
    PhoneNumber,
    PickupAddress,
    ProfileIcon,
    SiteEmail,
    SiteFavicon,
    SiteLogo,
    StaticPage,
    TikTok,
)


def site_logo(request):
    logo = SiteLogo.objects.first()
    return {'site_logo': logo}


def site_favicon(request):
    favicon = SiteFavicon.objects.first()
    return {'site_favicon': favicon}


def phone(request):
    phone = PhoneNumber.objects.first()
    return {'phone': phone}


def site_email(request):
    email = SiteEmail.objects.first()
    return {'site_email': email}


def instagram(request):
    instagram = Instagram.objects.first()
    return {'instagram': instagram}


def profile_icon(request):
    icon = ProfileIcon.objects.first()
    return {'profile_icon': icon}


def cart_icon(request):
    icon = CartIcon.objects.first()
    return {'cart_icon': icon}


def tiktok(request):
    tiktok = TikTok.objects.first()
    return {'tiktok': tiktok}


def footer_info(request):
    info = FooterInfo.objects.first()
    return {'footer_info': info}


def order_availability(request):
    return {'orders_available': OrderAvailability.orders_available()}


def pickup_address(request):
    return {'pickup_address': PickupAddress.objects.first()}


def delivery_info(request):
    info = DeliveryInfo.objects.first()
    return {
        'delivery_info': info,
        'belpochta_note': info.belpochta_note if info else DEFAULT_BELPOCHTA_DELIVERY_NOTE,
        'evropochta_note': info.evropochta_note if info else DEFAULT_EVROPOCHTA_DELIVERY_NOTE,
    }


def payment_info(request):
    info = PaymentInfo.objects.first()

    def value(field, default):
        return getattr(info, field) if info else default

    return {
        'payment_info': info,
        'erip_note': value('erip_note', DEFAULT_ERIP_PAYMENT_NOTE),
        'cod_belpochta_note': value('cod_belpochta_note', DEFAULT_COD_BELPOCHTA_NOTE),
        'cod_evropochta_note': value('cod_evropochta_note', DEFAULT_COD_EVROPOCHTA_NOTE),
        'cod_pickup_note': value('cod_pickup_note', DEFAULT_COD_PICKUP_NOTE),
        'onsite_note': value('onsite_note', DEFAULT_ONSITE_PAYMENT_NOTE),
    }


def footer_pages(request):
    pages = StaticPage.objects.filter(is_published=True)
    return {'footer_pages': pages}


def payment_page(request):
    page = StaticPage.objects.filter(slug='payment').first()
    return {'payment_page': page}


def gender_categories(request):
    from django.db.models import Q

    from app_catalog.models import Category

    unisex = Q(products__gender__isnull=True)

    def menu(gender_q):
        # Категория попадает в меню, только если у неё есть активный товар
        # нужного пола (или унисекс) — пустые и неактивные не показываем.
        return (
            Category.objects
            .filter(is_active=True, has_gender=True)
            .filter(Q(products__is_active=True) & gender_q)
            .distinct()
            .order_by('order', 'name')
        )

    return {
        'categories_men': menu(Q(products__gender='M') | unisex),
        'categories_women': menu(Q(products__gender='F') | unisex),
    }


def general_categories(request):
    from app_catalog.models import Category
    return {
        'categories_general': Category.objects.filter(
            is_active=True, has_gender=False
        ).order_by('order', 'name'),
    }


def cart_count(request):
    try:
        from app_cart.models import Cart
        if request.session.session_key:
            cart = Cart.objects.filter(session_key=request.session.session_key).first()
            if cart:
                return {'cart_total_items': cart.total_items}
    except Exception:
        pass
    return {'cart_total_items': 0}
