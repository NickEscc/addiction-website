
#website/urls.py

from django.urls import path
from . import views
from website.consumer import PokerGameConsumer


urlpatterns = [
    path('', views.home, name='home'),  # Home page
    path('HowToPlay/', views.HowToPlay, name='HowToPlay'),  # How To Play page
    path('login/', views.login, name='login'),  # Login page
    path('join/', views.join, name='join'),  # Join logic
    # path('index/', views.index, name='index'),  # Index router
    path('game/', views.Game, name='game'),  # Poker game
    path('start-texas/', views.start_texas_game, name='start_texas'),  # Start Texas Hold'em
    # path('start-traditional/', views.start_traditional_game, name='start_traditional'),  # Start Traditional Poker
    # path('play/', views.game_interface, name='play'),  # Game interface
]
