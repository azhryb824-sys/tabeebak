from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Avg, Count

from .models import Doctor


def doctor_list(request):
    doctors = Doctor.objects.all().annotate(
        avg_rating=Avg("reviews__rating"),
        reviews_count=Count("reviews")
    )

    q = request.GET.get("q", "").strip()
    specialization = request.GET.get("specialization", "").strip()
    sort = request.GET.get("sort", "").strip()

    if q:
        doctors = doctors.filter(
            Q(name__icontains=q) |
            Q(specialization__icontains=q) |
            Q(bio__icontains=q)
        )

    if specialization:
        doctors = doctors.filter(specialization__iexact=specialization)

    if sort == "price_asc":
        doctors = doctors.order_by("price")
    elif sort == "price_desc":
        doctors = doctors.order_by("-price")
    elif sort == "rating":
        doctors = doctors.order_by("-avg_rating", "-reviews_count", "-id")
    elif sort == "experience":
        doctors = doctors.order_by("-experience_years")
    else:
        doctors = doctors.order_by("-id")

    context = {
        "doctors": doctors,
        "q": q,
        "selected_specialization": specialization,
        "selected_sort": sort,
    }
    return render(request, "doctors/doctor_list.html", context)


def doctor_detail(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)

    review_stats = doctor.reviews.aggregate(
        avg_rating=Avg("rating"),
        reviews_count=Count("id"),
    )

    latest_reviews = doctor.reviews.select_related(
        "patient",
        "appointment"
    ).order_by("-created_at")[:5]

    context = {
        "doctor": doctor,
        "review_stats": review_stats,
        "latest_reviews": latest_reviews,
    }
    return render(request, "doctors/doctor_detail.html", context)