# addiction/asgi.py

import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
import website.routing  # Adjust the import path based on your project structure

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'addiction.settings')
django.setup()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            website.routing.websocket_urlpatterns  # Ensure this is correctly defined
        )
    ),
})
