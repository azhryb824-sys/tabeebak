from django.urls import re_path
from .consumers import AppointmentChatConsumer

websocket_urlpatterns = [
    re_path(r"ws/appointments/(?P<appointment_id>\d+)/chat/$", AppointmentChatConsumer.as_asgi()),
]