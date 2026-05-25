from django.urls import path

from . import views

app_name = 'projects'

urlpatterns = [
    path(
        'list/',
        views.project_list,
        name='project_list',
    ),
    path(
        '<int:project_id>/',
        views.project_detail,
        name='project_detail',
    ),
    path(
        'create-project/',
        views.create_project,
        name='create_project',
    ),
]
