from datetime import datetime, time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db import models
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    ListingForm,
    ListingSlotForm,
    ListingSlotFormSet,
    validate_non_overlapping_slots,
)
from .models import (
    EV_CHARGER_LEVELS,
    EV_CONNECTOR_TYPES,
    PARKING_SPOT_SIZES,
    Listing,
    ListingSlot,
)
from .utils import (
    filter_listings,
    has_active_filters,
)

# Add this new function for API support
from django.http import JsonResponse
from django.template.loader import render_to_string


def user_listings_api(request, username):
    """API endpoint for paginated user listings"""
    page = int(request.GET.get("page", 1))
    listings_per_page = 10
    start = (page - 1) * listings_per_page
    end = start + listings_per_page

    # Get the host user
    host = get_object_or_404(User, username=username)

    # Use the same logic as user_listings to get sorted listings
    current_datetime = datetime.now()
    listings = Listing.objects.filter(user=host).distinct()
    available_listings = []
    unavailable_listings = []

    for listing in listings:
        is_available = listing.slots.filter(
            models.Q(end_date__gt=current_datetime.date())
            | models.Q(
                end_date=current_datetime.date(), end_time__gt=current_datetime.time()
            )
        ).exists()
        listing.user_profile_available = is_available
        if is_available:
            available_listings.append(listing)
        else:
            unavailable_listings.append(listing)

    # Sort and combine
    available_listings.sort(key=lambda x: -x.created_at.timestamp())
    unavailable_listings.sort(key=lambda x: -x.created_at.timestamp())
    sorted_listings = available_listings + unavailable_listings

    # Slice for pagination
    page_listings = sorted_listings[start:end]

    # Render HTML for these listings
    html = render_to_string(
        "listings/partials/listing_cards.html",
        {"listings": page_listings, "is_public_view": True},
        request=request,
    )

    return JsonResponse({"html": html, "has_more": len(sorted_listings) > end})


# Define an inline formset for editing (extra=0)
ListingSlotFormSetEdit = inlineformset_factory(
    Listing, ListingSlot, form=ListingSlotForm, extra=0, can_delete=True
)

# Define half-hour choices for use in the search form
HALF_HOUR_CHOICES = [
    (f"{hour:02d}:{minute:02d}", f"{hour:02d}:{minute:02d}")
    for hour in range(24)
    for minute in (0, 30)
]


def merge_listing_slots(listing):
    """
    Merge continuous or overlapping availability slots for the given listing.
    Two slots are merged if the end datetime of one equals or overlaps
    the start datetime of the next. The merged slot will span from the earliest
    start to the latest end among continuous/overlapping slots.
    """
    slots = list(listing.slots.all())
    if not slots:
        return

    # Convert each slot to a (start_datetime, end_datetime) tuple.
    intervals = []
    for slot in slots:
        start_dt = datetime.combine(slot.start_date, slot.start_time)
        end_dt = datetime.combine(slot.end_date, slot.end_time)
        intervals.append((start_dt, end_dt))

    # Sort intervals by start time.
    intervals.sort(key=lambda iv: iv[0])
    merged = []
    for interval in intervals:
        if not merged:
            merged.append(interval)
        else:
            last_start, last_end = merged[-1]
            # If the intervals overlap or are continuous (i.e. adjacent), merge them.
            if interval[0] <= last_end:
                merged[-1] = (last_start, max(last_end, interval[1]))
            else:
                merged.append(interval)

    # Update ListingSlot records: delete all current slots and create new ones.
    listing.slots.all().delete()
    for start_dt, end_dt in merged:
        ListingSlot.objects.create(
            listing=listing,
            start_date=start_dt.date(),
            start_time=start_dt.time(),
            end_date=end_dt.date(),
            end_time=end_dt.time(),
        )


@login_required
def create_listing(request):
    alert_message = ""
    if request.method == "POST":
        listing_form = ListingForm(request.POST)
        slot_formset = ListingSlotFormSet(request.POST, prefix="form")
        if listing_form.is_valid() and slot_formset.is_valid():
            try:
                validate_non_overlapping_slots(slot_formset)
            except Exception:
                alert_message = "Overlapping slots detected. Please correct."
                return render(
                    request,
                    "listings/create_listing.html",
                    {
                        "form": listing_form,
                        "slot_formset": slot_formset,
                        "alert_message": alert_message,
                    },
                )
            new_listing = listing_form.save(commit=False)
            new_listing.user = request.user
            new_listing.save()
            slot_formset.instance = new_listing
            slot_formset.save()
            # Merge continuous slots if they are present.
            merge_listing_slots(new_listing)
            messages.success(request, "Listing created successfully!")
            return redirect("view_listings")
        else:
            alert_message = "Please correct the errors below."
    else:
        listing_form = ListingForm()
        slot_formset = ListingSlotFormSet(prefix="form")
    return render(
        request,
        "listings/create_listing.html",
        {
            "form": listing_form,
            "slot_formset": slot_formset,
            "alert_message": alert_message,
        },
    )


@login_required
def edit_listing(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id, user=request.user)
    alert_message = ""
    current_dt = datetime.now()

    if request.method == "POST":
        # Create mutable copy of POST data
        post_data = request.POST.copy()

        # Explicitly handle the unchecked EV charger checkbox
        if "has_ev_charger" not in post_data:
            post_data["has_ev_charger"] = False

        listing_form = ListingForm(post_data, instance=listing)
        slot_formset = ListingSlotFormSetEdit(
            post_data, instance=listing, prefix="form"
        )
        if listing_form.is_valid() and slot_formset.is_valid():
            try:
                validate_non_overlapping_slots(slot_formset)
            except Exception:
                alert_message = "Overlapping slots detected. Please correct."
                return render(
                    request,
                    "listings/edit_listing.html",
                    {
                        "form": listing_form,
                        "slot_formset": slot_formset,
                        "listing": listing,
                        "alert_message": alert_message,
                    },
                )

            # Block editing if there is any pending booking.
            pending_bookings = listing.booking_set.filter(status="PENDING")
            if pending_bookings.exists():
                alert_message = (
                    "You cannot edit your listing while there is a pending booking. "
                    "Please accept or reject all pending bookings before editing."
                )
                return render(
                    request,
                    "listings/edit_listing.html",
                    {
                        "form": listing_form,
                        "slot_formset": slot_formset,
                        "listing": listing,
                        "alert_message": alert_message,
                    },
                )

            # Build new intervals from the formset.
            new_intervals = []
            for form in slot_formset:
                if form.cleaned_data.get("DELETE"):
                    continue
                start_date = form.cleaned_data.get("start_date")
                start_time = form.cleaned_data.get("start_time")
                end_date = form.cleaned_data.get("end_date")
                end_time = form.cleaned_data.get("end_time")
                if start_date and start_time and end_date and end_time:
                    st = (
                        start_time
                        if isinstance(start_time, time)
                        else datetime.strptime(start_time, "%H:%M").time()
                    )
                    et = (
                        end_time
                        if isinstance(end_time, time)
                        else datetime.strptime(end_time, "%H:%M").time()
                    )
                    start_dt = datetime.combine(start_date, st)
                    end_dt = datetime.combine(end_date, et)
                    new_intervals.append((start_dt, end_dt))

            # Merge intervals into non-overlapping ranges.
            new_intervals.sort(key=lambda iv: iv[0])
            merged_intervals = []
            for interval in new_intervals:
                if not merged_intervals:
                    merged_intervals.append(interval)
                else:
                    last_start, last_end = merged_intervals[-1]
                    if interval[0] <= last_end:
                        merged_intervals[-1] = (last_start, max(last_end, interval[1]))
                    else:
                        merged_intervals.append(interval)

            # BLOCK EDIT IF ANY NEW INTERVAL OVERLAPS WITH ANY APPROVED BOOKING SLOT
            active_bookings = listing.booking_set.filter(status="APPROVED")
            for booking in active_bookings:
                for slot in booking.slots.all():
                    booking_start = datetime.combine(slot.start_date, slot.start_time)
                    booking_end = datetime.combine(slot.end_date, slot.end_time)
                    for interval_start, interval_end in merged_intervals:
                        if (
                            interval_start < booking_end
                            and booking_start < interval_end
                        ):
                            alert_message = (
                                "Your changes conflict with an active booking. "
                                "You cannot edit when new availability overlaps with an approved booking."
                            )
                            return render(
                                request,
                                "listings/edit_listing.html",
                                {
                                    "form": listing_form,
                                    "slot_formset": slot_formset,
                                    "listing": listing,
                                    "alert_message": alert_message,
                                },
                            )

            listing_form.save()
            slot_formset.save()

            # Delete any timeslots that have already passed.
            for slot in listing.slots.all():
                slot_end = datetime.combine(slot.end_date, slot.end_time)
                if slot_end <= datetime.now():
                    slot.delete()

            # Merge continuous slots if needed.
            merge_listing_slots(listing)

            messages.success(request, "Listing updated successfully!")
            return redirect("manage_listings")
        else:
            alert_message = "Please correct the errors below."
    else:
        # GET: Pre-process timeslots.
        all_slots = listing.slots.all()
        non_passed_ids = [
            slot.id
            for slot in all_slots
            if datetime.combine(slot.end_date, slot.end_time) > current_dt
        ]
        non_passed_qs = listing.slots.filter(id__in=non_passed_ids)
        listing_form = ListingForm(instance=listing)
        slot_formset = ListingSlotFormSetEdit(
            instance=listing, prefix="form", queryset=non_passed_qs
        )
        # For any ongoing slot, update its initial start_time to the next half‑hour slot.
        for form in slot_formset.forms:
            slot = form.instance
            slot_start_dt = datetime.combine(slot.start_date, slot.start_time)
            slot_end_dt = datetime.combine(slot.end_date, slot.end_time)
            if slot_start_dt <= current_dt < slot_end_dt:
                minutes = current_dt.minute
                if minutes < 30:
                    new_minute = 30
                    new_hour = current_dt.hour
                else:
                    new_minute = 0
                    new_hour = current_dt.hour + 1
                    if new_hour >= 24:
                        new_hour -= 24
                form.initial["start_time"] = f"{new_hour:02d}:{new_minute:02d}"

    return render(
        request,
        "listings/edit_listing.html",
        {
            "form": listing_form,
            "slot_formset": slot_formset,
            "listing": listing,
            "alert_message": alert_message,
        },
    )


def view_listings(request):
    current_datetime = datetime.now()

    # This query returns listings with at least one slot that has not yet ended.
    all_listings = Listing.objects.filter(
        models.Q(slots__end_date__gt=current_datetime.date())
        | models.Q(
            slots__end_date=current_datetime.date(),
            slots__end_time__gt=current_datetime.time(),
        )
    ).distinct()

    error_messages = []
    warning_messages = []
    success_messages = []

    # Get success message from session if it exists
    success_message = request.session.pop("success_message", None)
    if success_message:
        success_messages.append(success_message)

    processed_listings, filter_errors, filter_warnings = filter_listings(
        all_listings, request
    )
    error_messages.extend(filter_errors)
    warning_messages.extend(filter_warnings)

    # Process the listings before pagination
    for listing in processed_listings:
        # Set availability data
        try:
            earliest_slot = listing.slots.earliest("start_date", "start_time")
            listing.available_from = earliest_slot.start_date
            listing.available_time_from = earliest_slot.start_time
            latest_slot = listing.slots.latest("end_date", "end_time")
            listing.available_until = latest_slot.end_date
            listing.available_time_until = latest_slot.end_time
        except listing.slots.model.DoesNotExist:
            listing.available_from = None
            listing.available_time_from = None
            listing.available_until = None
            listing.available_time_until = None

        # Explicitly mark listings as available in the main listings view
        listing.user_profile_available = True

    # Continue with pagination
    paginator = Paginator(processed_listings, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "listings": page_obj,
        "half_hour_choices": HALF_HOUR_CHOICES,
        "filter_type": request.GET.get("filter_type", "single"),
        "max_price": request.GET.get("max_price", ""),
        "search_lat": request.GET.get("lat"),
        "search_lng": request.GET.get("lng"),
        "radius": request.GET.get("radius"),
        "start_date": request.GET.get("start_date", ""),
        "end_date": request.GET.get("end_date", ""),
        "start_time": request.GET.get("start_time", ""),
        "end_time": request.GET.get("end_time", ""),
        "recurring_pattern": request.GET.get("recurring_pattern", "daily"),
        "recurring_start_date": request.GET.get("recurring_start_date", ""),
        "recurring_end_date": request.GET.get("recurring_end_date", ""),
        "recurring_start_time": request.GET.get("recurring_start_time", ""),
        "recurring_end_time": request.GET.get("recurring_end_time", ""),
        "recurring_weeks": request.GET.get("recurring_weeks", "4"),
        "recurring_overnight": "on" if request.GET.get("recurring_overnight") else "",
        "has_next": page_obj.has_next(),
        "next_page": int(page_number) + 1 if page_obj.has_next() else None,
        "error_messages": error_messages,
        "warning_messages": warning_messages,
        "success_messages": success_messages,
        "charger_level_choices": EV_CHARGER_LEVELS,
        "connector_type_choices": EV_CONNECTOR_TYPES,
        "parking_spot_sizes": PARKING_SPOT_SIZES,
        "has_active_filters": has_active_filters(request),
        "is_public_view": False,
    }

    if request.GET.get("ajax") == "1":
        return render(request, "listings/partials/listing_cards.html", context)
    return render(request, "listings/view_listings.html", context)


def map_view_listings(request):
    current_datetime = datetime.now()
    all_listings = Listing.objects.filter(
        models.Q(slots__end_date__gt=current_datetime.date())
        | models.Q(
            slots__end_date=current_datetime.date(),
            slots__end_time__gt=current_datetime.time(),
        )
    ).distinct()
    processed_listings, filter_errors, filter_warnings = filter_listings(
        all_listings, request
    )

    # Transform listings into a JSON-serializable format
    markers = []
    for listing in processed_listings:
        markers.append(
            {
                "id": listing.id,
                "title": listing.title,
                "lat": listing.latitude,
                "lng": listing.longitude,
                "price": str(listing.rent_per_hour),
                "rating": float(listing.avg_rating or 0),
                "location_name": listing.location_name or "",
                "has_ev_charger": listing.has_ev_charger,
                "charger_level": (
                    listing.ev_charger_level if listing.has_ev_charger else None
                ),
                "connector_type": (
                    listing.ev_connector_type if listing.has_ev_charger else None
                ),
                "size": listing.parking_spot_size,
            }
        )

    return JsonResponse({"markers": markers})


def manage_listings(request):
    owner_listings = Listing.objects.filter(user=request.user)
    for listing in owner_listings:
        listing.pending_bookings = listing.booking_set.filter(status="PENDING")
        listing.approved_bookings = listing.booking_set.filter(status="APPROVED")
    return render(
        request, "listings/manage_listings.html", {"listings": owner_listings}
    )


@login_required
def delete_listing(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id, user=request.user)
    active_bookings = listing.booking_set.filter(status__in=["PENDING", "APPROVED"])
    if active_bookings.exists():
        owner_listings = Listing.objects.filter(user=request.user)
        for lst in owner_listings:
            lst.pending_bookings = lst.booking_set.filter(status="PENDING")
            lst.approved_bookings = lst.booking_set.filter(status="APPROVED")
        return render(
            request,
            "listings/manage_listings.html",
            {
                "listings": owner_listings,
                "delete_error": "Cannot delete listing with pending bookings. Please handle those first.",
                "error_listing_id": listing_id,
            },
        )
    if request.method == "POST":
        listing.delete()
        return redirect("manage_listings")
    return render(request, "listings/confirm_delete.html", {"listing": listing})


def listing_reviews(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    reviews = listing.reviews.all()
    return render(
        request,
        "listings/listing_reviews.html",
        {"listing": listing, "reviews": reviews},
    )


def user_listings(request, username):
    # Get the host user
    host = get_object_or_404(User, username=username)

    # Check if the host is verified
    try:
        profile = host.profile  # Assuming you have a profile model related to User
        is_verified = profile.is_verified
    except (AttributeError, ObjectDoesNotExist):  # ← Specific exceptions
        is_verified = False

    # Redirect or show error if host is not verified
    if not is_verified:
        messages.error(request, "This user is not a verified host.")
        return redirect("home")  # Or another appropriate page

    # Continue with the existing code for verified hosts
    current_datetime = datetime.now()

    # Get all listings from this user
    listings = Listing.objects.filter(user=host).distinct()

    # Create two separate lists - available and unavailable
    available_listings = []
    unavailable_listings = []

    for listing in listings:
        is_available = listing.slots.filter(
            models.Q(end_date__gt=current_datetime.date())
            | models.Q(
                end_date=current_datetime.date(), end_time__gt=current_datetime.time()
            )
        ).exists()

        listing.user_profile_available = is_available

        if is_available:
            available_listings.append(listing)
        else:
            unavailable_listings.append(listing)

    # Sort each list by creation date (newest first)
    available_listings.sort(key=lambda x: -x.created_at.timestamp())
    unavailable_listings.sort(key=lambda x: -x.created_at.timestamp())

    # Combine the lists - available first, then unavailable
    sorted_listings = available_listings + unavailable_listings

    context = {
        "listings": sorted_listings,
        "host": host,
        "is_public_view": True,
        "source": "user_listings",
        "username": username,
        "total_count": len(sorted_listings),  # Add this line
    }
    return render(request, "listings/user_listings.html", context)


@login_required
def my_listings(request):
    """Shortcut to view the logged-in user's listings"""
    return redirect("user_listings", username=request.user.username)


def map_legend(request):
    return render(request, "listings/map_legend.html")
