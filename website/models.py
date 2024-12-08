from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from decimal import Decimal

#we need a custom user model to store the balance of the user

class CustomUser(AbstractUser):
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def deposit(self, amount):
        self.balance += Decimal(amount)
        self.save()

class Game(models.Model):
    name = models.CharField(max_length=255)
    entry_fee = models.DecimalField(max_digits=10, decimal_places=2)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_games',
        null = True
    )


    def __str__(self):
        return self.name

    def join_game(self, user):
        if user.balance < self.entry_fee:
            raise ValueError("Insufficient balance to join the game.")
        user.balance -= self.entry_fee
        user.save()

