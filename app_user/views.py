from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from app_cart.models import Cart
from app_order.models import Order
from .forms import PhoneAuthenticationForm, PhoneUserCreationForm, UserProfileForm
from .models import UserProfile


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

    def form_valid(self, form):
        response = super().form_valid(form)
        claim_guest_data(self.request, self.request.user)
        return response


class UserRegisterView(CreateView):
    template_name = 'app_user/register.html'
    form_class = PhoneUserCreationForm
    success_url = reverse_lazy('app_user:profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        claim_guest_data(self.request, self.object)
        UserProfile.objects.get_or_create(user=self.object)
        return response


class UserLogoutView(LogoutView):
    next_page = '/'


@login_required
def profile_dashboard(request):
    return render(request, 'app_user/profile.html')


@login_required
def profile_edit(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлён')
            return redirect('app_user:profile')
    else:
        form = UserProfileForm(instance=profile)
    return render(request, 'app_user/profile_edit.html', {'form': form})


class UserPasswordChangeView(PasswordChangeView):
    template_name = 'app_user/password_change.html'
    success_url = reverse_lazy('app_user:password_change_done')

    def form_valid(self, form):
        response = super().form_valid(form)
        update_session_auth_hash(self.request, form.user)
        messages.success(self.request, 'Пароль изменён')
        return response