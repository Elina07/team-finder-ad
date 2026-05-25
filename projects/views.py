import json
from http import HTTPStatus

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users.models import Skill
from .forms import ProjectForm
from .models import Project

ITEMS_PER_PAGE = 12
MAX_SKILLS_SUGGESTIONS = 10


def paginate_queryset(request, queryset, items_per_page=ITEMS_PER_PAGE):
    """Утилита для пагинации queryset"""
    paginator = Paginator(queryset, items_per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def get_project_or_404_json(project_id, user=None):
    """Получить проект или вернуть JsonResponse с ошибкой 404"""
    try:
        if user:
            project = Project.objects.get(id=project_id, owner=user)
        else:
            project = Project.objects.get(id=project_id)
        return project
    except Project.DoesNotExist:
        return None


def get_skill_or_404_json(skill_id):
    """Получить навык или вернуть JsonResponse с ошибкой 404"""
    try:
        return Skill.objects.get(id=skill_id)
    except Skill.DoesNotExist:
        return None


def project_list(request):
    projects_list = Project.objects.select_related('owner').prefetch_related(
        'skills'
    ).order_by('-created_at')

    all_skills = Skill.objects.values_list('name', flat=True).order_by('name')
    active_skill = request.GET.get('skill', '')

    if active_skill:
        projects_list = projects_list.filter(
            skills__name=active_skill
        ).distinct()

    page_obj = paginate_queryset(request, projects_list)

    query_prefix = f'skill={active_skill}&' if active_skill else ''

    context = {
        'page_obj': page_obj,
        'all_skills': all_skills,
        'active_skill': active_skill,
        'query_prefix': query_prefix,
    }
    return render(request, 'projects/project_list.html', context)


def project_detail(request, project_id):
    try:
        project = Project.objects.select_related('owner').prefetch_related(
            'participants', 'skills'
        ).get(id=project_id)
    except Project.DoesNotExist:
        return render(request, '404.html', status=404)

    context = {'project': project}
    return render(request, 'projects/project-details.html', context)


@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            project.participants.add(request.user)
            return redirect('projects:project_detail', project_id=project.id)
    else:
        form = ProjectForm()
    context = {'form': form, 'is_edit': False}
    return render(request, 'projects/create-project.html', context)


@login_required
def edit_project(request, project_id):
    try:
        project = Project.objects.get(id=project_id, owner=request.user)
    except Project.DoesNotExist:
        return render(request, '404.html', status=404)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect('projects:project_detail', project_id=project.id)
    else:
        form = ProjectForm(instance=project)
    context = {'form': form, 'is_edit': True}
    return render(request, 'projects/create-project.html', context)


@login_required
@require_http_methods(["POST"])
def toggle_participation(request, project_id):
    project = get_project_or_404_json(project_id)
    if project is None:
        return JsonResponse(
            {'error': 'Project not found'},
            status=HTTPStatus.NOT_FOUND
        )

    is_participant = project.participants.filter(
        id=request.user.id
    ).exists()

    if is_participant:
        project.participants.remove(request.user)
        is_participant = False
    else:
        project.participants.add(request.user)
        is_participant = True

    participants_data = []
    for member in project.participants.only(
        'id', 'name', 'surname', 'avatar'
    ).all():
        participants_data.append({
            'id': member.id,
            'name': f'{member.name} {member.surname}',
            'avatar_url': member.avatar.url if member.avatar else None,
            'is_owner': member.id == project.owner.id,
        })

    return JsonResponse({
        'status': 'ok',
        'is_participant': is_participant,
        'participants_count': project.participants.count(),
        'participants': participants_data,
    })


@login_required
@require_http_methods(["POST"])
def complete_project(request, project_id):
    project = get_project_or_404_json(project_id, user=request.user)
    if project is None:
        return JsonResponse(
            {'error': 'Project not found'},
            status=HTTPStatus.NOT_FOUND
        )

    if project.status == Project.OPEN:
        project.status = Project.CLOSED
        project.save()

    return JsonResponse({
        'status': 'ok',
        'project_status': project.status,
    })


def skill_search(request):
    """Автодополнение навыков для проектов"""
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
def add_skill(request, project_id):
    """Добавление навыка проекту"""
    project = get_project_or_404_json(project_id, user=request.user)
    if project is None:
        return JsonResponse(
            {'error': 'Project not found'},
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

    skill_exists = project.skills.filter(id=skill.id).exists()
    if not skill_exists:
        project.skills.add(skill)
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
def remove_skill(request, project_id, skill_id):
    """Удаление навыка из проекта"""
    project = get_project_or_404_json(project_id, user=request.user)
    if project is None:
        return JsonResponse(
            {'error': 'Project not found'},
            status=HTTPStatus.NOT_FOUND
        )

    skill = get_skill_or_404_json(skill_id)
    if skill is None:
        return JsonResponse(
            {'error': 'Skill not found'},
            status=HTTPStatus.NOT_FOUND
        )

    project.skills.remove(skill)
    return JsonResponse({'status': 'ok'})
