"""
ASGI config for addiction project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

# addiction/asgi.py

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import website.routing  # Adjust based on your app's name

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'addiction.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            website.routing.websocket_urlpatterns
        )
    ),
})
