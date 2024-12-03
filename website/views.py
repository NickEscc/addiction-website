
#website/view.py

import os
import uuid
import redis
from django.http import JsonResponse
from subprocess import Popen
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.safestring import mark_safe
import json

from website.Services.Logic.channel import ChannelError, MessageFormatError, MessageTimeout
from website.Services.Logic.player import Player
from website.Services.Logic.player_client import PlayerClientConnector

# Redis configuration
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(redis_url)



def index(request):
    """
    Renders the index page with a login button.
    """
    return render(request, "index.html")
def login_view(request):
    """
    Renders the login page. Clears session data to prompt for a new login.
    """
    # Clear session data to prevent automatic login
    request.session.flush()
    return render(request, "website/login.html")


@require_http_methods(["POST"])
def join(request):
    """
    Handles the login form submission, sets session data, and redirects to the game page.
    """
    player_name = request.POST.get("name")
    room_id = request.POST.get("room-id", "default-room")
    request.session["player-id"] = str(uuid.uuid4())
    request.session["player-name"] = player_name
    request.session["player-money"] = 1000  # Example starting money
    request.session["room-id"] = room_id  # Store room_id in session

    return redirect('game')  # Redirect to the game view
def logout_view(request):
    # Clear the session data
    request.session.flush()
    # Redirect to login page
    return redirect(reverse("index"))


# START GAME SERVICES
def start_texas_game(request):
    """
    Starts a Texas Hold'em Poker game service as a subprocess.
    """
    process = Popen(['python', 'website/Services/texasholdem_poker_service.py'])
    return JsonResponse({"status": "Texas Hold'em game started", "pid": process.pid})



def game(request):
    """
    Renders the game page with the player context.
    """
    if "player-id" not in request.session:
        return redirect('login')

    player_id = request.session["player-id"]
    player_name = request.session.get("player-name", "Guest")
    player_money = request.session.get("player-money", 0)
    room_id = request.session.get("room-id", "default-room")

    return render(request, "website/game.html", {
        "player_id": player_id,
        "player_name": player_name,
        "player_money": player_money,
        "room_id": room_id,
    })


# ADDITIONAL VIEWS
def home(request):
    return render(request, "home.html")


def HowToPlay(request):
    return render(request, "website/HowToPlay.html")


def login(request):
    return render(request, "website/login.html")


