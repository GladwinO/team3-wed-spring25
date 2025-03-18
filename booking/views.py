# bookings/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
import datetime as dt
from django.utils import timezone
from django.http import JsonResponse
from .models import Booking
from .forms import BookingForm, BookingSlotFormSet
from listings.models import Listing
from listings.forms import ReviewForm
from django.contrib import messages
from .utils import block_out_booking, restore_booking_availability


@login_required
def available_times(request):
    listing_id = request.GET.get("listing_id")
    date_str = request.GET.get("date")
    ref_date_str = request.GET.get("ref_date")  # reference date from first interval
    max_time_str = request.GET.get("max_time")  # optional for start_time update
    min_time_str = request.GET.get("min_time")  # optional for end_time update
    if not listing_id or not date_str:
        return JsonResponse({"times": []})
    try:
        booking_date = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"times": []})
    listing = get_object_or_404(Listing, pk=listing_id)

    # If a reference date is provided, get the listing slot covering it.
    ref_slot = None
    if ref_date_str:
        try:
            ref_date = dt.datetime.strptime(ref_date_str, "%Y-%m-%d").date()
        except ValueError:
            ref_date = None
        if ref_date:
            ref_slots = listing.slots.filter(
                start_date__lte=ref_date, end_date__gte=ref_date
            )
            if ref_slots.exists():
                ref_slot = ref_slots.first()

    # Get listing slots covering the requested booking_date.
    slots = listing.slots.filter(
        start_date__lte=booking_date, end_date__gte=booking_date
    )
    if ref_slot:
        slots = slots.filter(pk=ref_slot.pk)

    valid_times = set()
    for slot in slots:
        # Determine time range.
        if slot.start_time == slot.end_time:
            current_dt = dt.datetime.combine(booking_date, dt.time(0, 0))
            end_dt = current_dt + dt.timedelta(days=1)
        else:
            if booking_date == slot.start_date:
                current_dt = dt.datetime.combine(booking_date, slot.start_time)
            else:
                current_dt = dt.datetime.combine(booking_date, dt.time(0, 0))
            if booking_date == slot.end_date:
                end_dt = dt.datetime.combine(booking_date, slot.end_time)
            else:
                end_dt = dt.datetime.combine(
                    booking_date, dt.time(0, 0)
                ) + dt.timedelta(days=1)
        while current_dt < end_dt:
            valid_times.add(current_dt.strftime("%H:%M"))
            current_dt += dt.timedelta(minutes=30)
    times = sorted(valid_times)
    if max_time_str:
        times = [t for t in times if t <= max_time_str]
    if min_time_str:
        times = [t for t in times if t >= min_time_str]
    print(
        "Returning times for listing",
        listing_id,
        "on",
        booking_date,
        "ref_date=",
        ref_date_str,
        ":",
        times,
    )
    return JsonResponse({"times": times})


@login_required
def book_listing(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)

    # Prevent owners from booking their own listing.
    if request.user == listing.user:
        messages.error(request, "You cannot book your own parking spot.")
        return redirect("view_listings")

    if request.method == "POST":
        booking_form = BookingForm(request.POST)
        slot_formset = BookingSlotFormSet(
            request.POST,
            form_kwargs={"listing": listing},
        )
        # For each form, set the listing.
        for form in slot_formset.forms:
            form.listing = listing
        if booking_form.is_valid() and slot_formset.is_valid():
            booking = booking_form.save(commit=False)
            booking.user = request.user
            booking.listing = listing
            booking.status = "PENDING"
            booking.save()
            slot_formset.instance = booking
            slot_formset.save()
            total_hours = 0
            for slot in booking.slots.all():
                start_dt = dt.datetime.combine(slot.start_date, slot.start_time)
                end_dt = dt.datetime.combine(slot.end_date, slot.end_time)
                duration = (end_dt - start_dt).total_seconds() / 3600.0
                total_hours += duration
            booking.total_price = total_hours * float(listing.rent_per_hour)
            booking.save()
            messages.success(request, "Booking request created!")
            return redirect("my_bookings")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        booking_form = BookingForm()
        slot_formset = BookingSlotFormSet()
        # Pass the listing via form_kwargs
        slot_formset = BookingSlotFormSet(form_kwargs={"listing": listing})

    return render(
        request,
        "booking/book_listing.html",
        {
            "listing": listing,
            "booking_form": booking_form,
            "slot_formset": slot_formset,
        },
    )


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user)
    if booking.status == "APPROVED":
        restore_booking_availability(booking.listing, booking)
    booking.delete()
    return redirect("my_bookings")


@login_required
def manage_booking(request, booking_id, action):
    booking = get_object_or_404(Booking, pk=booking_id)
    if request.user != booking.listing.user:
        return redirect("my_bookings")
    if action == "approve":
        booking.status = "APPROVED"
        booking.save()
        block_out_booking(booking.listing, booking)
        # (Call block_out_booking(booking.listing, booking) here if you want to block times.)
    elif action == "decline":
        if booking.status == "APPROVED":
            restore_booking_availability(booking.listing, booking)
        booking.status = "DECLINED"
        booking.save()
        # (Call restore_booking_availability(booking.listing, booking) here if needed.)
    return redirect("manage_listings")


@login_required
def review_booking(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user)
    # Determine earliest slot start to decide if booking has started.
    earliest_slot = min(
        (
            dt.datetime.combine(slot.start_date, slot.start_time)
            for slot in booking.slots.all()
        ),
        default=None,
    )
    if earliest_slot:
        booking_datetime = timezone.make_aware(
            earliest_slot, timezone.get_current_timezone()
        )
        if timezone.now() < booking_datetime:
            return redirect("my_bookings")
    else:
        return redirect("my_bookings")

    if hasattr(booking, "review"):
        return redirect("my_bookings")

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.booking = booking
            review.listing = booking.listing
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
    now_naive = dt.datetime.now()
    for booking in user_bookings:
        slots_info = []
        for slot in booking.slots.all():
            slot_dt = dt.datetime.combine(slot.start_date, slot.start_time)
            has_started = now_naive >= slot_dt
            slots_info.append(
                {
                    "booking_datetime": slot_dt,
                    "has_started": has_started,
                    "slot": slot,
                }
            )
        booking.slots_info = slots_info
    return render(request, "booking/my_bookings.html", {"bookings": user_bookings})
