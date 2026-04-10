from django.urls import path
from . import views

app_name = "consultations"

urlpatterns = [
    path("followups/", views.followup_list, name="followup_list"),
    path("followups/create/", views.followup_create, name="followup_create"),
    path(
        "followups/create/from-appointment/<int:appointment_id>/",
        views.followup_create_from_appointment,
        name="followup_create_from_appointment"
    ),
    path("followups/<int:pk>/", views.followup_detail, name="followup_detail"),
    path("followups/<int:pk>/edit/", views.followup_edit, name="followup_edit"),
]
