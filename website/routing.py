# website/routing.py

from django.urls import re_path
from website.consumer import PokerGameConsumer

websocket_urlpatterns = [
    re_path(r'ws/Services/(?P<room_name>\w+)/$', PokerGameConsumer.as_asgi()),
]
