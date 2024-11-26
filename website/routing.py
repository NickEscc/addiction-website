from django.urls import re_path
from . import consumer

websocket_urlpatterns = [
    re_path(r'ws/poker/(?P<connection_channel>[^/]+)/$', consumer.PokerGameConsumer.as_asgi()),
]
