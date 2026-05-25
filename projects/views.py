import json

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from users.models import Skill
from .forms import ProjectForm
from .models import Project


def project_list(request):
    projects_list = Project.objects.select_related('owner').prefetch_related(
        'skills'
    ).order_by('-created_at')

    # Передаем список названий навыков (строки), а не объектов
    all_skills = Skill.objects.values_list('name', flat=True).order_by('name')
    active_skill = request.GET.get('skill', '')

    if active_skill:
        projects_list = projects_list.filter(
            skills__name=active_skill
        ).distinct()

    paginator = Paginator(projects_list, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    query_prefix = f'skill={active_skill}&' if active_skill else ''

    context = {
        'page_obj': page_obj,
        'all_skills': all_skills,
        'active_skill': active_skill,
        'query_prefix': query_prefix,
    }
    return render(request, 'projects/project_list.html', context)


def project_detail(request, project_id):
    project = get_object_or_404(
        Project.objects.select_related('owner').prefetch_related(
            'participants', 'skills'
        ),
        id=project_id,
    )
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
    project = get_object_or_404(
        Project, id=project_id, owner=request.user
    )
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
    project = get_object_or_404(Project, id=project_id)
    if request.user in project.participants.all():
        project.participants.remove(request.user)
        is_participant = False
    else:
        project.participants.add(request.user)
        is_participant = True

    participants_data = []
    for member in project.participants.all():
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
    project = get_object_or_404(
        Project, id=project_id, owner=request.user
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
    ).order_by('name')[:10]
    data = [{'id': skill.id, 'name': skill.name} for skill in skills]
    return JsonResponse(data, safe=False)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def add_skill(request, project_id):
    """Добавление навыка проекту"""
    project = get_object_or_404(
        Project, id=project_id, owner=request.user
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
        try:
            skill = Skill.objects.get(id=skill_id)
        except Skill.DoesNotExist:
            return JsonResponse({'error': 'Skill not found'}, status=404)
    else:
        skill, created = Skill.objects.get_or_create(name=name)

    if skill not in project.skills.all():
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
    project = get_object_or_404(
        Project, id=project_id, owner=request.user
    )
    skill = get_object_or_404(Skill, id=skill_id)
    project.skills.remove(skill)
    return JsonResponse({'status': 'ok'})
