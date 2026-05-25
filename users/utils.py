import re

from django.core.exceptions import ValidationError

from .models import User

PHONE_REGEX = r'^(\+7|8)\d{10}$'


def validate_phone(phone, exclude_pk=None):
    """Валидация телефонного номера"""
    if not phone:
        return phone

    phone = phone.replace(' ', '').replace('-', '')

    if not re.match(PHONE_REGEX, phone):
        raise ValidationError(
            'Введите номер в формате +7XXXXXXXXXX или 8XXXXXXXXXX.'
        )

    if phone.startswith('8'):
        phone = '+7' + phone[1:]

    queryset = User.objects.filter(phone=phone)
    if exclude_pk:
        queryset = queryset.exclude(pk=exclude_pk)

    if queryset.exists():
        raise ValidationError('Этот номер уже используется.')

    return phone


def validate_github_url(github_url):
    """Валидация GitHub ссылки"""
    if github_url and 'github.com' not in github_url:
        raise ValidationError('Введите ссылку на GitHub.')
    return github_url
