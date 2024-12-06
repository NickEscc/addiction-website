
from django.shortcuts import render


# Create your views here.
def home(request):
    return render(request, 'website/home.html')

def HowToPlay(request):
    return render(request, 'website/HowToPlay.html')

def HowItWorks(request):
    return render(request, 'website/HowItWorks.html')

def SignUp(request):
    return render (request, 'website/SignUp.html')
    
def Login(request):
    return render (request, 'website/Login.html')