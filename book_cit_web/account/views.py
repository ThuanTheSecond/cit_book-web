from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template import loader
from .forms import customUserCreationForm, loginForm

# Create your views here.
def loginView(request):
    
    if request.user.is_authenticated:
        logout(request)       
        
    form = loginForm(request.POST or None)
    next_url = request.POST.get('next', 'index')
    if request.method == 'POST':
        if form.is_valid():
            user = form.login(request.POST)
            if user:
                login(request, user)
                return redirect(next_url) # Redirect to a success page.
    return render(request, 'login.html', {'form': form })

def logoutView(request):
    logout(request)
    return redirect('index')

def registerView(request):
    form = customUserCreationForm()
    if request.method == 'POST':
        form = customUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    context = {
        'form' : form,
    }
    return render(request, 'register.html', context)