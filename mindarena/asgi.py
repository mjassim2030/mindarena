# mindarena/asgi.py
import os

# 1) Configure settings ASAP
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mindarena.settings")

# (Optional, explicit) ensure apps are ready before importing anything that hits models
import django
django.setup()

# 2) Build the HTTP app
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

# 3) Now import Channels bits and your routing (safe after setup)
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import main_app.routing

# 4) Multiplex HTTP + WebSocket
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(main_app.routing.websocket_urlpatterns)
    ),
})
