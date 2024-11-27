
#website/urls.py

from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),  # Home page
    path('', views.index, name='index'),

    path('HowToPlay/', views.HowToPlay, name='HowToPlay'),  # How To Play page
    path('login/', views.login, name='login'),  # Login page
    path('join/', views.join, name='join'),  # Join logic
    # path('index/', views.index, name='index'),  # Index router
    path('game/', views.game, name='game'),  # Poker game
    path('start_texas_game/', views.start_texas_game, name='start_texas_game'),  # Start Texas Hold'em
    # path('start-traditional/', views.start_traditional_game, name='start_traditional'),  # Start Traditional Poker
    # path('play/', views.game_interface, name='play'),  # Game interface
    path('logout/', views.logout_view, name='logout'),

]
