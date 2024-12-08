
#website/urls.py

from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),  # Home page
    path('', views.index, name='index'),

    path('HowToPlay/', views.HowToPlay, name='HowToPlay'),  # How To Play page
    #path('login/', views.login, name='login'),  # Login page removed for my new login page - andrew h
    path('join/', views.join, name='join'),  # Join logic
    # path('index/', views.index, name='index'),  # Index router
    path('game/', views.game, name='game'),  # Poker game
    path('start_texas_game/', views.start_texas_game, name='start_texas_game'),  # Start Texas Hold'em
    # path('start-traditional/', views.start_traditional_game, name='start_traditional'),  # Start Traditional Poker
    # path('play/', views.game_interface, name='play'),  # Game interface
    path('logout/', views.logout_view, name='logout'),
    path('deposit/', views.deposit_money, name='deposit_money'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('games/join/<int:game_id>/', views.join_game, name='join_game'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create_game/', views.create_game, name='create_game'),

    
]
