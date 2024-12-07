
from django.urls import path
from . import views


urlpatterns = [
    path('register/', views.register, name='register'),  # Route for registration page
    path('login/', views.login_view, name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('game-history/', views.game_history, name='game_history'),
    path('transaction-history/', views.transaction_history, name='transaction_history'),
    path('create/', views.create_game, name='create_game'),
    path('join/', views.join_game, name='join_game'),
    path('game-room/<str:game_code>/', views.game_room, name='game_room'),
]


