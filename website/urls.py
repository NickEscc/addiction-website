from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('index/', views.index, name='index'),
    path('accounts/login/', views.custom_login, name='account_login'),
    path('accounts/logout/', views.custom_logout, name='account_logout'),
    path('accounts/signup/', views.custom_signup, name='account_signup'),
    path('accounts/', include('allauth.urls')),

    path('join/', views.join, name='join'),
    path('game/', views.game, name='game'),
    path('howtoplay/', views.howtoplay, name='howtoplay'),
    path('howitworks/', views.howitworks, name='howitworks'),
    path('chips/', views.chips, name='chips'),
]
