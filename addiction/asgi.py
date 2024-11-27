# asgi.py
import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.sessions import SessionMiddlewareStack
from django.core.asgi import get_asgi_application
import website.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'addiction.settings')
django.setup()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": SessionMiddlewareStack(
        AuthMiddlewareStack(
            URLRouter(
                website.routing.websocket_urlpatterns
            )
        )
    ),
})
