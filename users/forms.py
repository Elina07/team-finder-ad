import re

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordChangeForm

from .models import User


class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = (
            'name',
            'surname',
            'email',
            'password',
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])

        if commit:
            user.save()

        return user


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()

        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            self.user = authenticate(
                email=email,
                password=password,
            )

            if not self.user:
                raise forms.ValidationError(
                    'Неверный имейл или пароль',
                )

        return cleaned_data


class EditProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            'name',
            'surname',
            'avatar',
            'about',
            'phone',
            'github_url',
        )

    def clean_phone(self):
        phone = self.cleaned_data['phone']

        pattern = r'^(8|\+7)\d{10}$'

        if not re.match(pattern, phone):
            raise forms.ValidationError(
                'Введите корректный номер телефона.',
            )

        if phone.startswith('8'):
            phone = '+7' + phone[1:]

        exists = User.objects.exclude(
            pk=self.instance.pk,
        ).filter(phone=phone).exists()

        if exists:
            raise forms.ValidationError(
                'Телефон уже используется.',
            )

        return phone

    def clean_github_url(self):
        github_url = self.cleaned_data['github_url']

        if github_url and 'github.com' not in github_url:
            raise forms.ValidationError(
                'Ссылка должна вести на GitHub.',
            )

        return github_url


class UserPasswordChangeForm(PasswordChangeForm):
    pass
