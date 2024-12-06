# website/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Home page
    path('index/', views.index, name='index'),

    path('HowToPlay/', views.HowToPlay, name='HowToPlay'),  # How To Play page
    path('login/', views.login, name='login'),  # Login page
    path('join/', views.join, name='join'),  # Join logic
    path('game/', views.game, name='game'),  # Poker game
    path('logout/', views.logout_view, name='logout'),
]
