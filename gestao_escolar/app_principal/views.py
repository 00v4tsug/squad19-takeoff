from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from .forms import CustomUserCreationForm

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

@login_required
def painel(request):
    if request.user.role == "ADMIN":
        return redirect("painel_admin")
    elif request.user.role == "PROFESSOR":
        return redirect("painel_professor")
    else:
        return redirect("painel_aluno")

@login_required
def painel_admin(request):
    return render(request, "painel_admin.html")

@login_required
def painel_professor(request):
    return render(request, "painel_professor.html")

@login_required
def painel_aluno(request):
    return render(request, "painel_aluno.html")
