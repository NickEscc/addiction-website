import os
import uuid
import redis
import logging
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

# Logging configuration
logger = logging.getLogger(__name__)

# Redis configuration (if used)
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(redis_url)


def index(request):
    """
    Renders the index page with a login button.
    """
    return render(request, "index.html")


def home(request):
    """
    Renders the home page.
    """
    return render(request, "home.html")


def login(request):
    """
    Renders the login page. Clears session data to prompt for a new login.
    """
    # Clear session data to prevent automatic login
    request.session.flush()
    return render(request, "website/login.html", {"error": None})


@require_http_methods(["POST"])
def join(request):
    """
    Handles the login form submission, sets session data, and redirects to the game page.
    """
    player_name = request.POST.get("name")
    room_id = request.POST.get("room_id", "default-room")  # Use 'room_id' instead of 'room-id'

    if not player_name:
        # Handle the case where the player name is not provided
        return render(request, "website/login.html", {"error": "Player name is required."})

    # Generate unique player ID
    player_id = str(uuid.uuid4())

    # Store player information in the session
    request.session["player_id"] = player_id
    request.session["player_name"] = player_name
    request.session["player_money"] = 1000.0  # Example starting money
    request.session["room_id"] = room_id

    logger.info(f"Player {player_name} (ID: {player_id}) is joining room {room_id}")

    return redirect('game')  # Redirect to the game view


def game(request):
    """
    Renders the game page with the player context.
    """
    # Retrieve player information from the session
    player_id = request.session.get('player_id')
    player_name = request.session.get('player_name')
    player_money = request.session.get('player_money')
    room_id = request.session.get('room_id')

    if not all([player_id, player_name, player_money, room_id]):
        # If any required information is missing, redirect to the login page
        return redirect('login')

    # Pass the data to the template
    context = {
        'player_id': player_id,
        'player_name': player_name,
        'player_money': player_money,
        'room_id': room_id,
    }
    return render(request, 'website/game.html', context)


def logout_view(request):
    """
    Clears the session data and redirects to the home page.
    """
    # Clear the session data
    request.session.flush()
    # Redirect to home page
    return redirect(reverse("home"))


def HowToPlay(request):
    """
    Renders the How To Play page.
    """
    return render(request, "website/HowToPlay.html")
