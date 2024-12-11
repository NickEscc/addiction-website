import uuid
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth import logout
from .forms import CustomSignUpForm
from django.contrib.auth.models import User

def custom_signup(request):
    if request.method == 'POST':
        form = CustomSignUpForm(request.POST)

        # Extract the email from the posted data
        email = request.POST.get('email')
        
        # Check if the email is already in use
        if email and User.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists. Please log in.')
            return redirect('account_login')

        # If the email is not in use, proceed with form validation
        if form.is_valid():
            user = form.save(request)  # Create the user
            messages.success(request, 'Account created successfully! You can now log in.')
            return redirect('account_login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomSignUpForm()
    
    return render(request, 'accounts/signup.html', {'form': form})

def custom_logout(request):
    logout(request)
    return redirect('home')

def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'accounts/login.html')

def home(request):
    return render(request, "home.html")

def index(request):
    return render(request, "index.html")

def howtoplay(request):
    return render(request, "website/howtoplay.html")

def chips(request):
    return render(request, "website/chips.html")

def howitworks(request):
    return render(request, "website/howitworks.html")

@login_required(login_url='account_login')
def join(request):
    if request.method == 'POST':
        player_name = request.POST.get('name')
        room_id = request.POST.get('room_id') or 'default-room'
        
        # Initialize player data
        player_id = str(uuid.uuid4())
        player_money = 1000.0

        # Save to session
        request.session['player_id'] = player_id
        request.session['player_name'] = player_name
        request.session['player_money'] = player_money
        request.session['room_id'] = room_id

        return redirect('game')
    else:
        return render(request, 'website/login.html', {})

@login_required(login_url='account_login')
def game(request):
    player_id = request.session.get('player_id')
    player_name = request.session.get('player_name', request.user.username)
    player_money = request.session.get('player_money', 1000.0)
    room_id = request.session.get('room_id', 'default-room')

    # If somehow session data is missing, initialize it again
    if not all([player_id, player_name, player_money, room_id]):
        request.session['player_id'] = str(uuid.uuid4())
        request.session['player_name'] = request.user.username
        request.session['player_money'] = 1000.0
        request.session['room_id'] = 'default-room'
        player_id = request.session['player_id']
        player_name = request.session['player_name']
        player_money = request.session['player_money']
        room_id = request.session['room_id']

    context = {
        'player_id': player_id,
        'player_name': player_name,
        'player_money': player_money,
        'room_id': room_id,
    }
    return render(request, 'website/game.html', context)
