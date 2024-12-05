from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Home page
    path('HowToPlay/', views.HowToPlay, name='HowToPlay'), #How To Play page
    path('HowItWorks/', views.HowItWorks, name='HowItWorks'), #How It Works page
    path('SignUp/', views.SignUp, name='SignUp'), #Sign Up page
]
