from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Skill, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('id', 'email', 'name', 'surname', 'is_staff')
    ordering = ('id',)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    search_fields = ('name',)
