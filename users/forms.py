import re

from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError

from .models import User


PHONE_REGEX = r'^(\+7|8)\d{10}$'


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль',
        })
    )


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8,
    )

    class Meta:
        model = User
        fields = ['name', 'surname', 'email', 'password']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class EditProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            'name', 'surname', 'avatar', 'about', 'phone', 'github_url',
        )

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone:
            return phone
        phone = phone.replace(' ', '').replace('-', '')
        if not re.match(PHONE_REGEX, phone):
            raise ValidationError(
                'Введите номер в формате +7XXXXXXXXXX или 8XXXXXXXXXX.'
            )
        if phone.startswith('8'):
            phone = '+7' + phone[1:]
        exists = User.objects.exclude(
            pk=self.instance.pk
        ).filter(phone=phone).exists()
        if exists:
            raise ValidationError('Этот номер уже используется.')
        return phone

    def clean_github_url(self):
        github_url = self.cleaned_data.get('github_url')
        if github_url and 'github.com' not in github_url:
            raise ValidationError('Введите ссылку на GitHub.')
        return github_url


class UserPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'id': 'old_password'})
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'id': 'new_password1'}),
        min_length=8,
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'id': 'new_password2'}),
        min_length=8,
    )
