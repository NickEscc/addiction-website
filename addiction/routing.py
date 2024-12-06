# addiction/routing.py

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.sessions import SessionMiddlewareStack
import website.routing

application = ProtocolTypeRouter({
    'websocket': SessionMiddlewareStack(
        URLRouter(
            website.routing.websocket_urlpatterns
        )
    ),
})
