from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from users.models import Skill

from .forms import ProjectForm
from .models import Project

def project_list(request):
    projects = Project.objects.select_related(
        'owner',
    ).prefetch_related(
        'skills',
    )

    active_skill = request.GET.get('skill')

    if active_skill:
        projects = projects.filter(
            skills__name=active_skill,
        )

    context = {
        'projects': projects,
        'all_skills': Skill.objects.all(),
        'active_skill': active_skill,
    }

    return render(
        request,
        'projects/project_list.html',
        context,
    )

def project_detail(request, project_id):
    project = get_object_or_404(
        Project.objects.prefetch_related(
            'participants',
            'skills',
        ),
        pk=project_id,
    )

    return render(
        request,
        'projects/project-details.html',
        {'project': project},
    )

@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)

        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()

            project.participants.add(request.user)

            return redirect(
                'projects:project_detail',
                project_id=project.id,
            )
    else:
        form = ProjectForm()

    return render(
        request,
        'projects/create-project.html',
        {
            'form': form,
            'is_edit': False,
        },
    )
