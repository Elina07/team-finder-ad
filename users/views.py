import json
from http import HTTPStatus

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from projects.models import Skill
from .forms import EditProfileForm, LoginForm, RegisterForm
from .models import User

ITEMS_PER_PAGE = 12
MAX_SKILLS_SUGGESTIONS = 10


def paginate_queryset(request, queryset, items_per_page=ITEMS_PER_PAGE):
    """Утилита для пагинации queryset"""
    paginator = Paginator(queryset, items_per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def get_user_or_404_json(user_id):
    """Получить пользователя или вернуть JsonResponse с ошибкой 404"""
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


def get_skill_or_404_json(skill_id):
    """Получить навык или вернуть JsonResponse с ошибкой 404"""
    try:
        return Skill.objects.get(id=skill_id)
    except Skill.DoesNotExist:
        return None


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('projects:project_list')
    else:
        form = RegisterForm()
    context = {'form': form}
    return render(request, 'users/register.html', context)


def login_view(request):
    error_message = None
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('projects:project_list')
            error_message = 'Неверный email или пароль'
    else:
        form = LoginForm()
    context = {
        'form': form,
        'error_message': error_message,
    }
    return render(request, 'users/login.html', context)


def logout_view(request):
    logout(request)
    return redirect('projects:project_list')


def user_list(request):
    participants_list = User.objects.prefetch_related('skills').order_by('-id')
    all_skills = Skill.objects.all().order_by('name')
    active_skill = request.GET.get('skill', '')

    if active_skill:
        participants_list = participants_list.filter(
            skills__name=active_skill
        ).distinct()

    page_obj = paginate_queryset(request, participants_list)

    query_prefix = f'skill={active_skill}&' if active_skill else ''

    skills_with_active = []
    for skill in all_skills:
        skills_with_active.append({
            'name': skill.name,
            'is_active': (skill.name == active_skill)
        })

    context = {
        'page_obj': page_obj,
        'all_skills': all_skills,
        'skills_with_active': skills_with_active,
        'active_skill': active_skill,
        'query_prefix': query_prefix,
    }
    return render(request, 'users/participants.html', context)


def user_detail(request, user_id):
    try:
        profile_user = User.objects.prefetch_related(
            'skills', 'owned_projects'
        ).get(id=user_id)
    except User.DoesNotExist:
        return render(request, '404.html', status=404)

    context = {'user': profile_user}
    return render(request, 'users/user-details.html', context)


@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = EditProfileForm(
            request.POST, request.FILES, instance=request.user
        )
        if form.is_valid():
            form.save()
            return redirect('users:user_detail', user_id=request.user.id)
    else:
        form = EditProfileForm(instance=request.user)
    context = {'form': form}
    return render(request, 'users/edit_profile.html', context)


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return redirect('users:user_detail', user_id=request.user.id)
    else:
        form = PasswordChangeForm(request.user)
    context = {'form': form}
    return render(request, 'users/change_password.html', context)


def user_skills_search(request):
    """Автодополнение навыков для пользователя"""
    query = request.GET.get('q', '')
    if len(query) < 1:
        return JsonResponse([], safe=False)

    skills = Skill.objects.filter(
        name__icontains=query
    ).order_by('name')[:MAX_SKILLS_SUGGESTIONS]

    data = [{'id': skill.id, 'name': skill.name} for skill in skills]
    return JsonResponse(data, safe=False)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def add_user_skill(request, user_id):
    """Добавление навыка пользователю"""
    if request.user.id != user_id:
        return JsonResponse(
            {'error': 'Forbidden'},
            status=HTTPStatus.FORBIDDEN
        )

    user = get_user_or_404_json(user_id)
    if user is None:
        return JsonResponse(
            {'error': 'User not found'},
            status=HTTPStatus.NOT_FOUND
        )

    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = {}

    skill_id = data.get('skill_id') or request.POST.get('skill_id')
    name = data.get('name') or request.POST.get('name')
    created = False
    added = False

    if skill_id:
        skill = get_skill_or_404_json(skill_id)
        if skill is None:
            return JsonResponse(
                {'error': 'Skill not found'},
                status=HTTPStatus.NOT_FOUND
            )
    else:
        skill, created = Skill.objects.get_or_create(name=name)

    skill_exists = user.skills.filter(id=skill.id).exists()
    if not skill_exists:
        user.skills.add(skill)
        added = True

    return JsonResponse({
        'id': skill.id,
        'name': skill.name,
        'created': created,
        'added': added,
    })


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def remove_user_skill(request, user_id, skill_id):
    """Удаление навыка у пользователя"""
    if request.user.id != user_id:
        return JsonResponse(
            {'error': 'Forbidden'},
            status=HTTPStatus.FORBIDDEN
        )

    user = get_user_or_404_json(user_id)
    if user is None:
        return JsonResponse(
            {'error': 'User not found'},
            status=HTTPStatus.NOT_FOUND
        )

    skill = get_skill_or_404_json(skill_id)
    if skill is None:
        return JsonResponse(
            {'error': 'Skill not found'},
            status=HTTPStatus.NOT_FOUND
        )

    user.skills.remove(skill)
    return JsonResponse({'status': 'ok'})
