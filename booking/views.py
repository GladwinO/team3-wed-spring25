# booking/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from datetime import datetime
from django.utils import timezone
from .models import Booking
from .forms import BookingForm
from listings.models import Listing
from listings.forms import ReviewForm
from django.contrib import messages


@login_required
def book_listing(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)

    # Prevent owners from booking their own spots
    if request.user == listing.user:
        messages.error(request, "You cannot book your own parking spot.")
        return redirect("view_listings")

    if request.method == "POST":
        form = BookingForm(request.POST, listing=listing)
        if form.is_valid():
            booking_date = form.cleaned_data["booking_date"]
            start_time = form.cleaned_data["start_time"]
            end_time = form.cleaned_data["end_time"]

            # Validate that the selected times are within the listing's available times
            if (
                start_time < listing.available_time_from
                or end_time > listing.available_time_until
                or end_time <= start_time
            ):
                form.add_error(
                    None,
                    "Please choose a time within the available range and ensure end time is after start time.",
                )
            else:
                # Calculate the booking duration in hours
                duration = (
                    datetime.combine(booking_date, end_time)
                    - datetime.combine(booking_date, start_time)
                ).total_seconds() / 3600
                total_price = float(listing.rent_per_hour) * duration

                booking = Booking(
                    user=request.user,
                    listing=listing,
                    booking_date=booking_date,
                    start_time=start_time,
                    end_time=end_time,
                    total_price=total_price,
                    status="PENDING",
                )
                booking.save()
                return redirect("my_bookings")
    else:
        form = BookingForm(listing=listing)

    return render(
        request, "booking/book_listing.html", {"form": form, "listing": listing}
    )


@login_required
def cancel_booking(request, booking_id):
    """
    Optional: Allows a user to cancel (delete) a booking.
    """
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user)
    booking.delete()
    return redirect("my_bookings")


@login_required
def manage_booking(request, booking_id, action):
    """
    Allows listing owners to approve or decline a booking request.
    """
    booking = get_object_or_404(Booking, pk=booking_id)

    # Ensure only the listing owner can approve/decline
    if request.user != booking.listing.user:
        return redirect("my_bookings")  # Redirect if unauthorized

    if action == "approve":
        booking.status = "APPROVED"
    elif action == "decline":
        booking.status = "DECLINED"
    booking.save()

    return redirect("manage_listings")


@login_required
def review_booking(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user)

    # Combine booking date and start time to get the booking datetime (naive)
    naive_booking_datetime = datetime.combine(booking.booking_date, booking.start_time)
    # Make it offset-aware using the current timezone.
    booking_datetime = timezone.make_aware(
        naive_booking_datetime, timezone.get_current_timezone()
    )

    if timezone.now() < booking_datetime:
        # Booking hasn't started yet; redirect or show an error.
        return redirect("my_bookings")

    # Check if this booking has already been reviewed
    if hasattr(booking, "review"):
        return redirect("my_bookings")

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.booking = booking
            review.listing = booking.listing  # set the listing from the booking
            review.user = request.user
            review.save()
            return redirect("my_bookings")
    else:
        form = ReviewForm()

    return render(
        request, "booking/review_booking.html", {"form": form, "booking": booking}
    )


@login_required
def my_bookings(request):
    user_bookings = Booking.objects.filter(user=request.user).order_by("-created_at")
    for booking in user_bookings:
        # Combine the date and time into a single naive datetime
        booking_datetime = datetime.combine(booking.booking_date, booking.start_time)

        # Compare with "now" as a naive datetime
        # (requires USE_TZ = False in settings.py OR at least ignoring timezone.now())
        now_naive = datetime.now()
        booking.has_started = now_naive >= booking_datetime
        booking.is_reviewed = hasattr(booking, "review")
        booking.can_be_reviewed = (
            booking.has_started
            and booking.status != "DECLINED"
            and booking.status != "PENDING"
        )

    return render(request, "booking/my_bookings.html", {"bookings": user_bookings})
