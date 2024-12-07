from django.contrib import admin
from .models import PlayerProfile, Transaction, PokerGame

# Register your models here.
admin.site.register(PlayerProfile)
admin.site.register(Transaction)
admin.site.register(PokerGame)