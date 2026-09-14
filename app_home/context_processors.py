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