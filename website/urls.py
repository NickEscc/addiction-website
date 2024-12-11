# website/urls.py
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Home page
    path('index/', views.index, name='index'),
    path('accounts/', include('allauth.urls')),  # allauth's own signup/login/logout
    
    path('join/', views.join, name='join'),  # New route for pre-game setup page
    path('game/', views.game, name='game'),
     path('howtoplay/', views.howtoplay, name='howtoplay'),
    path('howitworks/', views.howitworks, name='howitworks'),
     path('chips/', views.chips, name='chips'),

]
