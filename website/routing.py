# website/routing.py

from django.urls import re_path
from .consumer import PokerGameConsumer
from .Services.Logic.game_room import GameRoom


websocket_urlpatterns = [
    re_path(r'ws/Services/(?P<connection_channel>[^/]+)/$', PokerGameConsumer.as_asgi()),
    re_path(r'ws/game_room/(?P<room_id>\w+)/$', GameRoom.as_asgi()),

]
