from django.db import models
from django.contrib.auth.models import User

# Player Profile Model
class PlayerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    games_played = models.IntegerField(default=0)
    total_winnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return self.user.username

# Transaction Model
class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdraw', 'Withdraw'),
        ('bet', 'Bet'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES)
    stripe_transaction_id = models.CharField(max_length=255)  # Ensure it aligns with Stripe data
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - ${self.amount}"

# Poker Game Model
class PokerGame(models.Model):
    players = models.ManyToManyField(User, related_name="poker_games")
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    winner = models.ForeignKey(
        User, related_name="won_games", on_delete=models.SET_NULL, null=True, blank=True
    )
    pot = models.DecimalField(max_digits=10, decimal_places=2)
    game_log = models.TextField(null=True, blank=True)
    game_code = models.CharField(max_length=6, unique=True, null=True, blank=True)

    def generate_game_code(self):
        """Generate a unique 6-character alphanumeric game code."""
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        while PokerGame.objects.filter(game_code=code).exists():  # Ensure uniqueness
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self.game_code = code

    def save(self, *args, **kwargs):
        """Override save method to automatically generate the code before saving."""
        if not self.game_code:
            self.generate_game_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Game {self.id} - Pot: ${self.pot} - Code: {self.game_code}"



