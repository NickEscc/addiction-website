from django.contrib import admin

# Register your models here.

from .models import CustomUser, Game

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'balance')

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'entry_fee')