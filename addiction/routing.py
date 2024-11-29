# addiction/routing.py

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import website.routing

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(
            website.routing.websocket_urlpatterns
        )
    ),
})
