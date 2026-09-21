from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UsernameField
from django.contrib.auth import get_user_model

from .utils import normalize_phone
from .models import UserProfile

User = get_user_model()


class PhoneAuthenticationForm(AuthenticationForm):
    """Вход по номеру телефона и паролю."""

    username = UsernameField(label='Телефон', widget=forms.TextInput(attrs={
        'autofocus': True,
        'inputmode': 'tel',
        'placeholder': '+375 (29) XXX-XX-XX',
    }))

    def clean_username(self):
        username = normalize_phone(self.cleaned_data['username'])
        if not username:
            raise forms.ValidationError('Укажите номер в формате +375 (29) XXX-XX-XX.')
        return username


class PhoneUserCreationForm(UserCreationForm):
    """Регистрация: телефон + пароль. Email не запрашивается."""

    username = forms.CharField(label='Телефон', widget=forms.TextInput(attrs={
        'autofocus': True,
        'inputmode': 'tel',
        'placeholder': '+375 (29) XXX-XX-XX',
    }))

    class Meta:
        model = User
        fields = ('username',)

    def clean_username(self):
        username = normalize_phone(self.cleaned_data['username'])
        if not username:
            raise forms.ValidationError('Укажите номер в формате +375 (29) XXX-XX-XX.')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Пользователь с таким номером уже зарегистрирован.')
        return username


class UserProfileForm(forms.ModelForm):
    """Форма редактирования профиля: ФИО, телефон, адрес."""

    class Meta:
        model = UserProfile
        fields = ('full_name', 'phone', 'address')
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Иванов Иван Иванович'}),
            'phone': forms.TextInput(attrs={'placeholder': '+375 (29) XXX-XX-XX', 'inputmode': 'tel'}),
            'address': forms.Textarea(attrs={'placeholder': 'Город, улица, дом, квартира', 'rows': 3}),
        }