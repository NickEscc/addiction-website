from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm
from django.contrib.auth.views import LogoutView
from .models import PokerGame, Transaction

#Registration View
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            # Save the form to create the user
            user = form.save()
            # Log the user in automatically after registration
            login(request, user)
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            return redirect('login')  # Redirect to home page after successful registration
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        # Authenticate the user manually (simple version, you could use Django's built-in form here)
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')  # Redirect to a home page or dashboard after login
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'users/login.html')


class CustomLogoutView(LogoutView):
    next_page = 'login' #Redirect to login page after logout


#Game History
def game_history(request):
    games = PokerGame.objects.filter(players=request.user).order_by("-start_time")
    return render(request, "users/game_history.html", {"games": games})


#Transaction History
def transaction_history(request):
    transactions = Transaction.objects.filter(user=request.user).order_by("-timestamp")
    return render(request, "users/transaction_history.html", {"transactions": transactions})

@login_required
def create_game(request):
    """Create a new game room and generate a unique code."""
    game = PokerGame.objects.create(pot=0.00)  # You can set other game attributes as needed
    game.players.add(request.user)  # Add the current user to the game as the first player
    game.save()
    return redirect('game_room', game_code=game.game_code)
    #Redirects to the game room page

@login_required
def join_game(request):
    """Join a game room by entering a game code."""
    if request.method == 'POST':
        game_code = request.POST.get('game_code')
        try:
            game = PokerGame.objects.get(game_code=game_code)
            if game.players.count() < 6:  # Assuming max 6 players
                game.players.add(request.user)  # Add the user to the game
                game.save()
                return redirect('game_room', game_code=game.game_code)  # Redirect to the game room
            else:
                messages.error(request, 'This game is full.')
        except PokerGame.DoesNotExist:
            messages.error(request, 'Invalid game code.')
    return render(request, 'users/join_game.html')

def game_room(request, game_code):
    """Show details of a game room."""
    game = PokerGame.objects.get(game_code=game_code)
    return render(request, 'users/game_room.html', {'game': game})