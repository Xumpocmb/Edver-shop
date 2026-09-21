from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from app_cart.models import Cart, Order

from .forms import PhoneAuthenticationForm, PhoneUserCreationForm


def claim_guest_data(request, user):
    """Привязывает корзину и заказы гостя (session_key) к аккаунту."""
    cart = Cart.get_or_create(request)
    if cart.user is None or cart.user != user:
        cart.user = user
        cart.save(update_fields=['user'])
    Order.objects.filter(
        session_key=request.session.session_key,
        user__isnull=True,
    ).update(user=user)


class UserLoginView(LoginView):
    template_name = 'app_user/login.html'
    form_class = PhoneAuthenticationForm
    redirect_authenticated_user = True
    next_page = reverse_lazy('app_user:profile')


class UserRegisterView(CreateView):
    template_name = 'app_user/register.html'
    form_class = PhoneUserCreationForm
    success_url = reverse_lazy('app_user:profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        claim_guest_data(self.request, self.object)
        return response


class UserLogoutView(LogoutView):
    next_page = '/'


@login_required
def profile_dashboard(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')[:10]
    context = {'orders': orders}
    return render(request, 'app_user/profile.html', context)
