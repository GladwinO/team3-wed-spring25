# bookings/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
import datetime as dt
from django.utils import timezone
from django.http import JsonResponse
from .models import Booking, BookingSlot
from .forms import (
    BookingForm,
    BookingSlotFormSet,
    BookingSlotForm,
)
from listings.models import Listing
from listings.forms import ReviewForm, HALF_HOUR_CHOICES
from django.db import transaction
from .utils import (
    block_out_booking,
    restore_booking_availability,
    generate_recurring_dates,
    generate_booking_slots,
)
from accounts.models import Notification


@login_required
def available_times(request):
    listing_id = request.GET.get("listing_id")
    date_str = request.GET.get("date")
    ref_date_str = request.GET.get("ref_date")
    max_time_str = request.GET.get("max_time")
    min_time_str = request.GET.get("min_time")
    if not listing_id or not date_str:
        return JsonResponse({"times": []})
    try:
        booking_date = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"times": []})
    listing = get_object_or_404(Listing, pk=listing_id)

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

    slots = listing.slots.filter(
        start_date__lte=booking_date, end_date__gte=booking_date
    )
    if ref_slot:
        slots = slots.filter(pk=ref_slot.pk)

    valid_times = set()
    for slot in slots:
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
        while current_dt <= end_dt:
            valid_times.add(current_dt.strftime("%H:%M"))
            current_dt += dt.timedelta(minutes=30)
    times = sorted(valid_times)

    # Filter out past times for today's date
    today = dt.date.today()
    if booking_date == today:
        # Get current time
        now = dt.datetime.now()

        # Calculate the next available time slot
        current_minutes = now.minute
        current_hour = now.hour

        # Round up to the nearest half hour
        if current_minutes < 30:
            next_slot_minutes = 30
            next_slot_hour = current_hour
        else:
            next_slot_minutes = 0
            next_slot_hour = current_hour + 1

        # Format as HH:MM string
        next_slot_str = f"{next_slot_hour:02d}:{next_slot_minutes:02d}"

        # Filter out times before the next valid slot
        times = [t for t in times if t >= next_slot_str]

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
    error_messages = []
    success_messages = []

    if request.user == listing.user:
        error_messages.append("You cannot book your own parking spot.")
        return redirect("view_listings")

    # Create initial data with user's email
    initial_data = {}
    if request.user.is_authenticated:
        initial_data["email"] = request.user.email

    # Create form with initial data
    if request.method == "POST":
        booking_form = BookingForm(request.POST)
        is_recurring = request.POST.get("is_recurring") == "true"

        if booking_form.is_valid():
            try:
                with transaction.atomic():
                    if not is_recurring:
                        # Handle regular (non-recurring) booking
                        booking = booking_form.save(commit=False)
                        booking.user = request.user
                        booking.listing = listing
                        booking.status = "PENDING"
                        booking.save()  # Save so we can use it for formset instance

                        slot_formset = BookingSlotFormSet(
                            request.POST,
                            instance=booking,
                            form_kwargs={"listing": listing},
                            prefix="form",
                        )
                        for form in slot_formset.forms:
                            form.listing = listing

                        if slot_formset.is_valid():
                            slot_formset.save()

                            if booking.slots.exists():
                                tz = timezone.get_current_timezone()

                                def combine_slot(date, time):
                                    dt_obj = dt.datetime.combine(date, time)
                                    return timezone.make_aware(dt_obj, tz)

                                overall_start = min(
                                    combine_slot(s.start_date, s.start_time)
                                    for s in booking.slots.all()
                                )
                                overall_end = max(
                                    combine_slot(s.end_date, s.end_time)
                                    for s in booking.slots.all()
                                )
                                valid = False
                                for avail in listing.slots.all():
                                    avail_start = combine_slot(
                                        avail.start_date, avail.start_time
                                    )
                                    avail_end = combine_slot(
                                        avail.end_date, avail.end_time
                                    )
                                    if (
                                        overall_start >= avail_start
                                        and overall_end <= avail_end
                                    ):
                                        valid = True
                                        break
                                if not valid:
                                    raise ValueError(
                                        "Booking must be within a single availability slot."
                                    )

                            total_hours = 0
                            for slot in booking.slots.all():
                                start_dt = dt.datetime.combine(
                                    slot.start_date, slot.start_time
                                )
                                end_dt = dt.datetime.combine(
                                    slot.end_date, slot.end_time
                                )
                                duration = (end_dt - start_dt).total_seconds() / 3600.0
                                total_hours += duration
                            booking.total_price = total_hours * float(
                                listing.rent_per_hour
                            )
                            booking.save()

                            # Create notification for the listing owner
                            Notification.objects.create(
                                sender=request.user,
                                recipient=listing.user,
                                subject=f"New Booking Request for {listing.title}",
                                content=f"{request.user.username} requested to book your spot '{listing.title}'. "
                                f"Please review and approve or decline this booking.",
                                notification_type="BOOKING",
                            )

                            success_messages.append("Booking request created!")
                            return redirect("my_bookings")
                        else:
                            raise ValueError(
                                "Please fix the errors in the booking form."
                            )
                    else:
                        # Handle recurring booking
                        start_date = request.POST.get("recurring-start_date")
                        start_time = request.POST.get("recurring-start_time")
                        end_time = request.POST.get("recurring-end_time")
                        pattern = request.POST.get("recurring_pattern", "daily")
                        is_overnight = request.POST.get("recurring-overnight") == "on"

                        if pattern == "daily":
                            end_date = request.POST.get("recurring-end_date")
                            if not all([start_date, start_time, end_time, end_date]):
                                raise ValueError(
                                    "Start date, end date, start time, end time required for recurring bookings."
                                )
                            start_date = dt.datetime.strptime(
                                start_date, "%Y-%m-%d"
                            ).date()
                            start_time = dt.datetime.strptime(
                                start_time, "%H:%M"
                            ).time()
                            end_time = dt.datetime.strptime(end_time, "%H:%M").time()
                            end_date = dt.datetime.strptime(end_date, "%Y-%m-%d").date()
                            if end_date < start_date:
                                raise ValueError(
                                    "End date must be on or after start date."
                                )
                            dates = generate_recurring_dates(
                                start_date, "daily", end_date=end_date
                            )
                        elif pattern == "weekly":
                            if not all([start_date, start_time, end_time]):
                                raise ValueError(
                                    "Start date, start time, end time required for recurring bookings."
                                )
                            start_date = dt.datetime.strptime(
                                start_date, "%Y-%m-%d"
                            ).date()
                            start_time = dt.datetime.strptime(
                                start_time, "%H:%M"
                            ).time()
                            end_time = dt.datetime.strptime(end_time, "%H:%M").time()
                            weeks_str = request.POST.get("recurring-weeks")
                            if not weeks_str:
                                raise ValueError(
                                    "Number of weeks is required for weekly recurring pattern."
                                )
                            weeks = int(weeks_str)
                            if weeks <= 0 or weeks > 52:
                                raise ValueError(
                                    "Number of weeks must be between 1 and 52."
                                )
                            dates = generate_recurring_dates(
                                start_date, "weekly", weeks=weeks
                            )

                        if start_time >= end_time and not is_overnight:
                            raise ValueError(
                                "Start time must be before end time unless overnight booking is selected."
                            )

                        booking_slots = generate_booking_slots(
                            dates, start_time, end_time, is_overnight
                        )

                        unavailable_dates = []
                        for slot in booking_slots:
                            start_dt = dt.datetime.combine(
                                slot["start_date"], slot["start_time"]
                            )
                            end_dt = dt.datetime.combine(
                                slot["end_date"], slot["end_time"]
                            )
                            start_dt = timezone.make_aware(start_dt)
                            end_dt = timezone.make_aware(end_dt)
                            if not listing.is_available_for_range(start_dt, end_dt):
                                date_str = slot["start_date"].strftime("%Y-%m-%d")
                                unavailable_dates.append(date_str)
                        if unavailable_dates:
                            error_msg = "Some of those times unavailable. Please review timeslots and try again."
                            raise ValueError(error_msg)

                        booking = booking_form.save(commit=False)
                        booking.user = request.user
                        booking.listing = listing
                        booking.status = "PENDING"
                        booking.save()

                        total_hours = 0
                        for slot_data in booking_slots:
                            slot = BookingSlot(
                                booking=booking,
                                start_date=slot_data["start_date"],
                                start_time=slot_data["start_time"],
                                end_date=slot_data["end_date"],
                                end_time=slot_data["end_time"],
                            )
                            slot.save()
                            start_dt = dt.datetime.combine(
                                slot_data["start_date"], slot_data["start_time"]
                            )
                            end_dt = dt.datetime.combine(
                                slot_data["end_date"], slot_data["end_time"]
                            )
                            duration = (end_dt - start_dt).total_seconds() / 3600.0
                            total_hours += duration
                        booking.total_price = total_hours * float(listing.rent_per_hour)
                        booking.save()

                        # Create notification for the listing owner
                        Notification.objects.create(
                            sender=request.user,
                            recipient=listing.user,
                            subject=f"New Recurring Booking Request for {listing.title}",
                            content=f"User {request.user.username} has requested \
                                a recurring booking for your parking spot '{listing.title}'. "
                            f"This booking includes {len(booking_slots)} dates. "
                            f"Please review and approve or decline this booking.",
                            notification_type="BOOKING",
                        )

                        success_messages.append(
                            f"Recurring booking created successfully for {len(booking_slots)} dates!"
                        )
                        return redirect("my_bookings")

            except ValueError as e:
                error_messages.append(str(e))
                slot_formset = BookingSlotFormSet(
                    form_kwargs={"listing": listing}, prefix="form"
                )
            except Exception as e:
                error_messages.append(f"An error occurred: {str(e)}")
                slot_formset = BookingSlotFormSet(
                    form_kwargs={"listing": listing}, prefix="form"
                )
        else:
            slot_formset = BookingSlotFormSet(
                request.POST, form_kwargs={"listing": listing}, prefix="form"
            )
            error_messages.append("Please fix the errors below.")
    else:
        booking_form = BookingForm(initial=initial_data)
        slot_formset = BookingSlotFormSet(
            form_kwargs={"listing": listing}, prefix="form"
        )

    recurring_form = BookingSlotForm(prefix="recurring", listing=listing)

    return render(
        request,
        "booking/book_listing.html",
        {
            "listing": listing,
            "booking_form": booking_form,
            "slot_formset": slot_formset,
            "recurring_form": recurring_form,
            "half_hour_choices": HALF_HOUR_CHOICES,
            "error_messages": error_messages,
            "success_messages": success_messages,
        },
    )


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user)

    # Create notification for the listing owner about the cancellation
    Notification.objects.create(
        sender=request.user,
        recipient=booking.listing.user,
        subject=f"Booking Canceled for {booking.listing.title}",
        content=f"User {request.user.username} canceled their booking for your spot '{booking.listing.title}'.",
        notification_type="BOOKING",
    )

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
        # First check if there are any conflicting bookings
        conflicts_found = False
        conflicting_bookings = []

        # Get all pending bookings for this listing except the current one
        other_pending_bookings = Booking.objects.filter(
            listing=booking.listing, status="PENDING"
        ).exclude(pk=booking_id)

        # Get all slots for the current booking
        current_booking_slots = booking.slots.all()

        # For each of the current booking's slots, check for conflicts with other pending bookings
        for current_slot in current_booking_slots:
            current_start = timezone.make_aware(
                dt.datetime.combine(current_slot.start_date, current_slot.start_time)
            )
            current_end = timezone.make_aware(
                dt.datetime.combine(current_slot.end_date, current_slot.end_time)
            )

            # Check each pending booking for conflicts
            for other_booking in other_pending_bookings:
                # Skip bookings we've already marked as conflicting
                if other_booking in conflicting_bookings:
                    continue

                # Check each slot in the other booking
                for other_slot in other_booking.slots.all():
                    other_start = timezone.make_aware(
                        dt.datetime.combine(
                            other_slot.start_date, other_slot.start_time
                        )
                    )
                    other_end = timezone.make_aware(
                        dt.datetime.combine(other_slot.end_date, other_slot.end_time)
                    )

                    # Check if the intervals overlap
                    if other_start < current_end and current_start < other_end:
                        conflicts_found = True
                        if other_booking not in conflicting_bookings:
                            conflicting_bookings.append(other_booking)
                        break  # No need to check other slots in this booking

        # Now approve the current booking
        booking.status = "APPROVED"
        booking.save()
        block_out_booking(booking.listing, booking)

        # Create notification for the user that their booking was approved
        Notification.objects.create(
            sender=request.user,
            recipient=booking.user,
            subject=f"Booking Approved for {booking.listing.title}",
            content=f"Your booking request for the parking spot '{booking.listing.title}' has been approved."
            f"You can now use this spot according to your booking schedule.",
            notification_type="BOOKING",
        )

        # If conflicts were found, decline those conflicting bookings
        if conflicts_found:
            for conflicting_booking in conflicting_bookings:
                # Skip if somehow this booking was already approved or declined
                if conflicting_booking.status != "PENDING":
                    continue

                # Mark the booking as declined
                conflicting_booking.status = "DECLINED"
                conflicting_booking.save()

                # Notify the user that their booking was declined due to conflict
                Notification.objects.create(
                    sender=request.user,
                    recipient=conflicting_booking.user,
                    subject=f"Booking Declined for {booking.listing.title}",
                    content=f"Your booking request for the parking spot '{booking.listing.title}' \
                        has been declined because another booking for the same time slot was approved first.",
                    notification_type="BOOKING",
                )

    elif action == "decline":
        if booking.status == "APPROVED":
            restore_booking_availability(booking.listing, booking)
        booking.status = "DECLINED"
        booking.save()

        # Create notification for the user that their booking was declined
        Notification.objects.create(
            sender=request.user,
            recipient=booking.user,
            subject=f"Booking Declined for {booking.listing.title}",
            content=f"Your booking request for the parking spot '{booking.listing.title}' has been declined."
            f"Please check for other available spots or contact the owner for more information.",
            notification_type="BOOKING",
        )

    return redirect("manage_listings")


@login_required
def review_booking(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user)
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

            # Notify the listing owner about the new review
            notify_owner_listing_reviewed(review)

            return redirect("my_bookings")
    else:
        form = ReviewForm()
    return render(
        request, "booking/review_booking.html", {"form": form, "booking": booking}
    )


@login_required
def my_bookings(request):
    # Get all bookings for current user
    all_bookings = Booking.objects.filter(user=request.user)

    # Create separate lists for different priorities
    approved_unreviewed = []
    other_bookings = []
    approved_reviewed = []

    # Sort bookings into categories
    for booking in all_bookings:
        # Check if booking has been reviewed
        has_review = hasattr(booking, "review")

        if booking.status == "APPROVED":
            if has_review:
                # Lowest priority: Approved bookings that have been reviewed
                approved_reviewed.append(booking)
            else:
                # Highest priority: Approved bookings that haven't been reviewed
                approved_unreviewed.append(booking)
        else:
            # Medium priority: Other bookings (pending/declined)
            other_bookings.append(booking)

    # Sort each category
    approved_unreviewed.sort(key=lambda x: x.updated_at, reverse=True)
    other_bookings.sort(key=lambda x: x.created_at, reverse=True)
    approved_reviewed.sort(key=lambda x: x.updated_at, reverse=True)

    # Combine all lists in priority order
    sorted_bookings = approved_unreviewed + other_bookings + approved_reviewed

    # Process booking slots
    for booking in sorted_bookings:
        # Get all slots for this booking
        slots = booking.slots.all().order_by("start_date", "start_time")

        # Format the slots information for display
        slots_info = []
        for slot in slots:
            slot_info = {
                "date": slot.start_date,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
            }
            slots_info.append(slot_info)

        # Add slots_info attribute to the booking object
        booking.slots_info = slots_info

    return render(request, "booking/my_bookings.html", {"bookings": sorted_bookings})


def notify_owner_booking_created(booking):
    """Create a notification for the owner when a booking is created."""
    owner = booking.listing.user
    listing_title = booking.listing.title
    booker_username = booking.user.username

    # Create notification for the owner
    Notification.objects.create(
        sender=booking.user,
        recipient=owner,
        subject=f"New Booking Request for {listing_title}",
        content=f"User {booker_username} has requested to book your parking spot '{listing_title}'. "
        f"Please review and approve or decline this booking.",
        notification_type="BOOKING",
    )


def notify_owner_booking_canceled(booking):
    """Create a notification for the owner when a booking is canceled."""
    owner = booking.listing.user
    listing_title = booking.listing.title
    booker_username = booking.user.username

    # Create notification for the owner
    Notification.objects.create(
        sender=booking.user,
        recipient=owner,
        subject=f"Booking Canceled for {listing_title}",
        content=f"User {booker_username} has canceled their booking for your parking spot '{listing_title}'.",
        notification_type="BOOKING",
    )


def notify_user_booking_approved(booking):
    """Create a notification for the user when their booking is approved."""
    listing_title = booking.listing.title
    owner_username = booking.listing.user.username

    # Create notification for the booker
    Notification.objects.create(
        sender=booking.listing.user,
        recipient=booking.user,
        subject=f"Booking Approved for {listing_title}",
        content=f"Your booking request for the spot '{listing_title}' by {owner_username} has been approved.",
        notification_type="BOOKING",
    )


def notify_owner_listing_reviewed(review):
    """Create a notification for the owner when their listing is reviewed."""
    listing = review.listing
    owner = listing.user
    reviewer_username = review.user.username
    review_rating = review.rating

    # Create notification for the owner
    Notification.objects.create(
        sender=review.user,
        recipient=owner,
        subject=f"New Review for {listing.title}",
        content=f"User {reviewer_username} left a {review_rating}-star review for your listing '{listing.title}'.",
        notification_type="BOOKING",
    )
