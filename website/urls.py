from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Home page
    path('HowToPlay/', views.how_to_play, name='how_to_play'), #How To Play page
]
