# website/routing.py

from django.urls import re_path
from .consumer import PokerGameConsumer

websocket_urlpatterns = [
    re_path(r'ws/Services/(?P<connection_channel>[^/]+)/$', PokerGameConsumer.as_asgi()),
]
