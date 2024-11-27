from django.urls import path
# from website.consumer import  EchoConsumer
from website.consumer import PokerGameConsumer

websocket_urlpatterns = [
    path("ws/Services/<str:connection_channel>/", PokerGameConsumer.as_asgi()),
    # path("ws/Services/<str:connection_channel>/", EchoConsumer.as_asgi()),

]
