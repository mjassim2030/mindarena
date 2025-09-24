# main_app/routing.py
from django.urls import re_path
from .consumers import LiveSessionConsumer, CourseSessionsConsumer

websocket_urlpatterns = [
    re_path(r"^ws/live/(?P<pk>\d+)/$", LiveSessionConsumer.as_asgi()),
    re_path(r"^ws/courses/(?P<course_id>\d+)/$", CourseSessionsConsumer.as_asgi()),
]
