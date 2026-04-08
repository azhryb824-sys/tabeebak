import json
from datetime import timedelta
from django.utils import timezone

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from doctors.models import Doctor
from .models import Appointment, AppointmentMessage


def _is_admin_user(user):
    return getattr(user, "user_type", "") == "admin" or user.is_staff


class AppointmentChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]
        self.appointment_id = self.scope["url_route"]["kwargs"]["appointment_id"]
        self.room_group_name = f"appointment_chat_{self.appointment_id}"

        if not self.user.is_authenticated:
            await self.close()
            return

        if not await self.user_can_access_appointment():
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        timing = await self.get_chat_timing_data()

        await self.send(text_data=json.dumps({
            "event": "chat_status",
            "doctor_started_chat": timing["doctor_started_chat"],
            "chat_closed": timing["chat_closed"],
            "remaining_seconds": timing["remaining_seconds"],
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except:
            return

        # =========================
        # 🎥 WebRTC SIGNALING
        # =========================
        if data.get("event") in ["offer", "answer", "ice"]:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "webrtc_signal",
                    "data": data
                }
            )
            return

        # =========================
        # 💬 CHAT
        # =========================
        content = (data.get("message") or "").strip()
        if not content:
            return

        can_send, error = await self.can_send()
        if not can_send:
            await self.send(text_data=json.dumps({
                "event": "error",
                "message": error
            }))
            return

        message = await self.save_message(content)
        timing = await self.get_chat_timing_data()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "broadcast_message",
                "data": {
                    "event": "chat_message",
                    "message": message["message"],
                    "sender": message["sender"],
                    "sender_type": message["sender_type"],
                    "created_at": message["created_at"],
                    "doctor_started_chat": timing["doctor_started_chat"],
                    "chat_closed": timing["chat_closed"],
                    "remaining_seconds": timing["remaining_seconds"],
                }
            }
        )

    # =========================
    # 🔥 SEND CHAT MESSAGE
    # =========================

    async def broadcast_message(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    # =========================
    # 🎥 SEND WEBRTC SIGNAL
    # =========================

    async def webrtc_signal(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    # =========================
    # ACCESS
    # =========================

    @sync_to_async
    def user_can_access_appointment(self):
        try:
            appointment = Appointment.objects.select_related("patient", "doctor").get(id=self.appointment_id)
        except Appointment.DoesNotExist:
            return False

        if appointment.patient_id == self.user.id:
            return True

        doctor = Doctor.objects.filter(user=self.user).first()
        if doctor and appointment.doctor_id == doctor.id:
            return True

        if _is_admin_user(self.user):
            return True

        return False

    # =========================
    # TIMING
    # =========================

    @sync_to_async
    def get_chat_timing_data(self):
        appointment = Appointment.objects.select_related("doctor").get(id=self.appointment_id)

        doctor_user = getattr(appointment.doctor, "user", None)

        first = None
        if doctor_user:
            first = AppointmentMessage.objects.filter(
                appointment=appointment,
                sender=doctor_user
            ).order_by("created_at").first()

        if not first:
            return {
                "doctor_started_chat": False,
                "chat_closed": False,
                "remaining_seconds": None
            }

        expires = first.created_at + timedelta(minutes=15)
        now = timezone.now()

        closed = now > expires
        remaining = max(int((expires - now).total_seconds()), 0)

        return {
            "doctor_started_chat": True,
            "chat_closed": closed,
            "remaining_seconds": remaining
        }

    # =========================
    # PERMISSION
    # =========================

    @sync_to_async
    def can_send(self):
        appointment = Appointment.objects.select_related("doctor", "patient").get(id=self.appointment_id)

        timing = self.get_chat_timing_data_sync(appointment)

        if timing["chat_closed"]:
            return False, "انتهت مدة الجلسة"

        doctor = Doctor.objects.filter(user=self.user).first()
        is_doctor = doctor and appointment.doctor_id == doctor.id

        if is_doctor:
            return True, ""

        if appointment.patient_id == self.user.id:
            if not timing["doctor_started_chat"]:
                return False, "انتظر حتى يبدأ الطبيب"

        return True, ""

    def get_chat_timing_data_sync(self, appointment):
        doctor_user = getattr(appointment.doctor, "user", None)

        first = None
        if doctor_user:
            first = AppointmentMessage.objects.filter(
                appointment=appointment,
                sender=doctor_user
            ).order_by("created_at").first()

        if not first:
            return {
                "doctor_started_chat": False,
                "chat_closed": False,
            }

        expires = first.created_at + timedelta(minutes=15)

        return {
            "doctor_started_chat": True,
            "chat_closed": timezone.now() > expires,
        }

    # =========================
    # SAVE MESSAGE
    # =========================

    @sync_to_async
    def save_message(self, content):
        appointment = Appointment.objects.get(id=self.appointment_id)

        msg = AppointmentMessage.objects.create(
            appointment=appointment,
            sender=self.user,
            content=content
        )

        sender_type = "patient"

        doctor = Doctor.objects.filter(user=self.user).first()
        if doctor and appointment.doctor_id == doctor.id:
            sender_type = "doctor"

        elif _is_admin_user(self.user):
            sender_type = "admin"

        return {
            "message": msg.content,
            "sender": self.user.get_full_name().strip() or self.user.username,
            "sender_type": sender_type,
            "created_at": msg.created_at.strftime("%H:%M")
        }