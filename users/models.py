from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from io import BytesIO
from PIL import Image, ImageDraw
import random


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')

        email = self.normalize_email(email)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        return self.create_user(email, password, **extra_fields)


class Skill(models.Model):
    name = models.CharField(
        max_length=124,
        unique=True,
    )

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        unique=True,
    )
    name = models.CharField(
        max_length=124,
    )
    surname = models.CharField(
        max_length=124,
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
    )
    phone = models.CharField(
        max_length=12,
        unique=True,
        blank=True,
    )
    github_url = models.URLField(
        blank=True,
    )
    about = models.TextField(
        max_length=256,
        blank=True,
    )
    skills = models.ManyToManyField(
        Skill,
        related_name='users',
        blank=True,
    )
    is_active = models.BooleanField(
        default=True,
    )
    is_staff = models.BooleanField(
        default=False,
    )
    created_at = models.DateTimeField(
        default=timezone.now,
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'surname']

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.avatar:
            self.generate_avatar()

        super().save(*args, **kwargs)

    def generate_avatar(self):
        colors = [
            '#8E9AAF',
            '#A4C3B2',
            '#84A59D',
            '#95B8D1',
        ]

        image = Image.new(
            'RGB',
            (200, 200),
            random.choice(colors),
        )

        draw = ImageDraw.Draw(image)

        first_letter = self.name[0].upper()

        draw.text(
            (80, 70),
            first_letter,
            fill='white',
        )

        buffer = BytesIO()
        image.save(buffer, format='PNG')

        filename = (
            f'{self.name.lower()}_avatar.png'
        )

        self.avatar.save(
            filename,
            ContentFile(buffer.getvalue()),
            save=False,
        )
