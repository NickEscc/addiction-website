
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
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.db import transaction

from website.Services.Logic.channel import ChannelError, MessageFormatError, MessageTimeout
from website.Services.Logic.player import Player
from website.Services.Logic.player_client import PlayerClientConnector

from .models import Game
from decimal import Decimal
from .forms import GameForm
from django.contrib import messages


# Redis configuration
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(redis_url)

@login_required
def create_game(request):
    if request.method == 'POST':
        form = GameForm(request.POST)
        if form.is_valid():
            game = form.save(commit=False)
            game.created_by = request.user
            game.save()
            messages.success(request, 'Game created successfully!')
            return redirect('dashboard')  # Redirect to dashboard after creation
    else:
        form = GameForm()
    return render(request, 'create_game.html', {'form': form})

@login_required
def dashboard(request):
    # Fetch the user's balance and the list of active games
    user_balance = request.user.balance  # Assuming `CustomUser` has a `balance` field
    active_games = Game.objects.all()  # Fetch all active games
    return render(request, 'dashboard.html', {'balance': user_balance, 'games': active_games})

@login_required
@transaction.atomic
def join_game(request, game_id):
    game = Game.objects.get(id=game_id)
    try:
        game.join_game(request.user)
        messages.success(request, f"Successfully joined the game: {game.name}")
    except ValueError as e:
        messages.error(request, f"Could not join game: {e}")
    return redirect('dashboard')  # Replace with your desired redirect

# Create a new player client connector

@login_required
@transaction.atomic
def deposit_money(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive.")
            request.user.balance += Decimal(amount)
            request.user.save()
            messages.success(request, f"Successfully added ${amount:.2f} to your balance.")
        except ValueError as e:
            messages.error(request, f"Invalid amount: {e}")
    return redirect('dashboard')

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

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


