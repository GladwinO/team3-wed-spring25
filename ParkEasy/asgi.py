import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
import messaging.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ParkEasy.settings")
django.setup()

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(messaging.routing.websocket_urlpatterns)
        ),
    }
)
