from .models import FooterInfo, Instagram, PhoneNumber, SiteLogo


def site_logo(request):
    logo = SiteLogo.objects.first()
    return {'site_logo': logo}


def phone(request):
    phone = PhoneNumber.objects.first()
    return {'phone': phone}


def instagram(request):
    instagram = Instagram.objects.first()
    return {'instagram': instagram}


def footer_info(request):
    info = FooterInfo.objects.first()
    return {'footer_info': info}


def gender_categories(request):
    from django.db.models import Q

    from app_catalog.models import Category
    cats = Category.objects.filter(is_active=True, has_gender=True).order_by('order', 'name')
    unisex = Q(products__gender__isnull=True)
    return {
        'categories_men': cats.filter(Q(products__gender='M') | unisex).distinct(),
        'categories_women': cats.filter(Q(products__gender='F') | unisex).distinct(),
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
