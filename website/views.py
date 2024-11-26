import os
import uuid
import redis
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from website.Services.Logic.channel import ChannelError, MessageFormatError, MessageTimeout
from website.Services.Logic.player import Player
from website.Services.Logic.player_client import PlayerClientConnector

# Redis configuration
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(redis_url)

def index(request):
    if "player-id" not in request.session:
        # return render(request, "index.html", {"template": "login.html"})
        return redirect(reverse('login'))  # Redirect to login page if not logged in

    return render(request, "index.html", {
        "template": "game.html",
        "player_id": request.session["player-id"],
        "player_name": request.session["player-name"],
        "player_money": request.session["player-money"],
    })

@require_http_methods(["POST"])
def join(request):
    name = request.POST.get("name")
    room_id = request.POST.get("room-id")
    request.session["player-id"] = str(uuid.uuid4())
    request.session["player-name"] = name
    request.session["player-money"] = 1000
    request.session["room-id"] = room_id if room_id else None
    return redirect(reverse("index"))

def home(request):
    return render(request, 'home.html')

def HowToPlay(request):
    return render(request, 'website/HowToPlay.html')

def login(request):
    return render(request, 'website/login.html')


# @csrf_exempt
# def texasholdem_poker_game(request):
#     return poker_game(request, "texas-holdem-poker:lobby")
# @csrf_exempt
# def traditional_poker_game(request):
#     return poker_game(request, "traditional-poker:lobby")


