from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from .forms import EditProfileForm
from .forms import LoginForm
from .forms import RegisterForm
from .models import Skill
from .models import User

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)

            return redirect('projects:project_list')
    else:
        form = RegisterForm()

    return render(
        request,
        'users/register.html',
        {'form': form},
    )


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            login(request, form.user)

            return redirect('projects:project_list')
    else:
        form = LoginForm()

    return render(
        request,
        'users/login.html',
        {'form': form},
    )
