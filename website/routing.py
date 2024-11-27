from django.urls import path
from website.consumer import PokerGameConsumer

websocket_urlpatterns = [
    path("ws/Services/<str:connection_channel>/", PokerGameConsumer.as_asgi()),
]
