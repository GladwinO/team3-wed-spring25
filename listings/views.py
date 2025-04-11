from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
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
from .models import EV_CHARGER_LEVELS, EV_CONNECTOR_TYPES, Listing, ListingSlot
from .utils import calculate_distance, extract_coordinates, has_active_filters

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

    max_price = request.GET.get("max_price")
    filter_type = request.GET.get("filter_type", "single")

    if max_price:
        try:
            max_price_val = float(max_price)
            all_listings = all_listings.filter(rent_per_hour__lte=max_price_val)
        except ValueError:
            pass

    error_messages = []
    warning_messages = []

    if filter_type == "single":
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        start_time = request.GET.get("start_time")
        end_time = request.GET.get("end_time")
        if any([start_date, end_date, start_time, end_time]):
            try:
                user_start_str = f"{start_date} {start_time}"
                user_end_str = f"{end_date} {end_time}"
                user_start_dt = datetime.strptime(user_start_str, "%Y-%m-%d %H:%M")
                user_end_dt = datetime.strptime(user_end_str, "%Y-%m-%d %H:%M")
                filtered = []
                for listing in all_listings:
                    if listing.is_available_for_range(user_start_dt, user_end_dt):
                        filtered.append(listing)
                all_listings = filtered
            except ValueError:
                pass

    elif filter_type == "multiple":
        try:
            interval_count = int(request.GET.get("interval_count", "0"))
        except ValueError:
            interval_count = 0

        intervals = []
        for i in range(1, interval_count + 1):
            s_date = request.GET.get(f"start_date_{i}")
            e_date = request.GET.get(f"end_date_{i}")
            s_time = request.GET.get(f"start_time_{i}")
            e_time = request.GET.get(f"end_time_{i}")
            if s_date and e_date and s_time and e_time:
                try:
                    s_dt = datetime.strptime(f"{s_date} {s_time}", "%Y-%m-%d %H:%M")
                    e_dt = datetime.strptime(f"{e_date} {e_time}", "%Y-%m-%d %H:%M")
                    intervals.append((s_dt, e_dt))
                except ValueError:
                    continue

        if intervals:
            filtered = []
            for listing in all_listings:
                available_for_all = True
                for s_dt, e_dt in intervals:
                    if not listing.is_available_for_range(s_dt, e_dt):
                        available_for_all = False
                        break
                if available_for_all:
                    filtered.append(listing)
            all_listings = filtered

    elif filter_type == "recurring":
        r_start_date = request.GET.get("recurring_start_date")
        r_start_time = request.GET.get("recurring_start_time")
        r_end_time = request.GET.get("recurring_end_time")
        pattern = request.GET.get("recurring_pattern", "daily")
        overnight = request.GET.get("recurring_overnight") == "on"
        continue_with_filter = True

        if r_start_date and r_start_time and r_end_time:
            try:
                intervals = []
                start_date_obj = datetime.strptime(r_start_date, "%Y-%m-%d").date()
                s_time = datetime.strptime(r_start_time, "%H:%M").time()
                e_time = datetime.strptime(r_end_time, "%H:%M").time()
                if s_time >= e_time and not overnight:
                    error_messages.append(
                        "Start time must be before end time unless overnight booking is selected"
                    )
                    continue_with_filter = False
                if pattern == "daily":
                    r_end_date = request.GET.get("recurring_end_date")
                    if not r_end_date:
                        error_messages.append(
                            "End date is required for daily recurring pattern"
                        )
                        continue_with_filter = False
                    else:
                        end_date_obj = datetime.strptime(r_end_date, "%Y-%m-%d").date()
                        if end_date_obj < start_date_obj:
                            error_messages.append(
                                "End date must be on or after start date"
                            )
                            continue_with_filter = False
                        else:
                            days_count = (end_date_obj - start_date_obj).days + 1
                            if days_count > 90:
                                warning_messages.append(
                                    "Daily recurring pattern spans over 90 days, results may be limited"
                                )
                            if continue_with_filter:
                                for day_offset in range(days_count):
                                    current_date = start_date_obj + timedelta(
                                        days=day_offset
                                    )
                                    s_dt = datetime.combine(current_date, s_time)
                                    end_date_for_slot = current_date + timedelta(
                                        days=1 if overnight else 0
                                    )
                                    e_dt = datetime.combine(end_date_for_slot, e_time)
                                    intervals.append((s_dt, e_dt))
                elif pattern == "weekly":
                    try:
                        weeks_str = request.GET.get("recurring_weeks")
                        if not weeks_str:
                            error_messages.append(
                                "Number of weeks is required for weekly recurring pattern"
                            )
                            continue_with_filter = False
                        else:
                            weeks = int(weeks_str)
                            if weeks <= 0:
                                error_messages.append(
                                    "Number of weeks must be positive"
                                )
                                continue_with_filter = False
                            elif weeks > 52:
                                warning_messages.append(
                                    "Weekly recurring pattern spans over 52 weeks, results may be limited"
                                )
                            if continue_with_filter:
                                for week_offset in range(weeks):
                                    current_date = start_date_obj + timedelta(
                                        weeks=week_offset
                                    )
                                    s_dt = datetime.combine(current_date, s_time)
                                    end_date_for_slot = current_date + timedelta(
                                        days=1 if overnight else 0
                                    )
                                    e_dt = datetime.combine(end_date_for_slot, e_time)
                                    intervals.append((s_dt, e_dt))
                    except ValueError:
                        error_messages.append("Invalid number of weeks")
                        continue_with_filter = False

                if continue_with_filter and intervals:
                    filtered = []
                    for listing in all_listings:
                        available_for_all = True
                        for s_dt, e_dt in intervals:
                            if overnight and s_time >= e_time:
                                evening_available = listing.is_available_for_range(
                                    s_dt, datetime.combine(s_dt.date(), time(23, 59))
                                )
                                morning_available = listing.is_available_for_range(
                                    datetime.combine(e_dt.date(), time(0, 0)), e_dt
                                )
                                if not (evening_available and morning_available):
                                    available_for_all = False
                                    break
                            elif not listing.is_available_for_range(s_dt, e_dt):
                                available_for_all = False
                                break
                        if available_for_all:
                            filtered.append(listing)
                    all_listings = filtered
            except ValueError:
                error_messages.append("Invalid date or time format")

            if not continue_with_filter:
                all_listings = Listing.objects.none()

    if request.GET.get("has_ev_charger") == "on":
        all_listings = all_listings.filter(has_ev_charger=True)

        # Apply additional EV filters only if has_ev_charger is selected
        charger_level = request.GET.get("charger_level")
        if charger_level:
            all_listings = all_listings.filter(charger_level=charger_level)

        connector_type = request.GET.get("connector_type")
        if connector_type:
            all_listings = all_listings.filter(connector_type=connector_type)

    if isinstance(all_listings, list):
        all_listings.sort(key=lambda x: x.id, reverse=True)
    else:
        all_listings = all_listings.order_by("-id")  # Note the minus sign

    processed_listings = []

    search_lat = request.GET.get("lat")
    search_lng = request.GET.get("lng")
    radius = request.GET.get("radius")

    if search_lat and search_lng:
        try:
            search_lat = float(search_lat)
            search_lng = float(search_lng)

            for listing in all_listings:
                try:
                    listing_lat, listing_lng = extract_coordinates(listing.location)
                    distance = calculate_distance(
                        search_lat, search_lng, listing_lat, listing_lng
                    )
                    listing.distance = distance
                    if radius:
                        radius = float(radius)
                        if distance <= radius:
                            processed_listings.append(listing)
                    else:
                        processed_listings.append(listing)
                except ValueError:
                    listing.distance = None
                    processed_listings.append(listing)
        except ValueError:
            error_messages.append("Invalid coordinates provided")
            processed_listings = list(all_listings)
    else:
        for listing in all_listings:
            listing.distance = None
            processed_listings.append(listing)

    if search_lat and search_lng:
        processed_listings.sort(
            key=lambda x: x.distance if x.distance is not None else float("inf")
        )

    for listing in processed_listings:
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

    page_number = request.GET.get("page", 1)
    paginator = Paginator(processed_listings, 10)
    page_obj = paginator.get_page(page_number)

    context = {
        "listings": page_obj,
        "half_hour_choices": HALF_HOUR_CHOICES,
        "filter_type": filter_type,
        "max_price": max_price or "",
        "search_lat": search_lat,
        "search_lng": search_lng,
        "radius": radius,
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
        "charger_level_choices": EV_CHARGER_LEVELS,
        "connector_type_choices": EV_CONNECTOR_TYPES,
        "has_active_filters": has_active_filters(request),
    }

    if request.GET.get("ajax") == "1":
        return render(request, "listings/partials/listing_cards.html", context)
    return render(request, "listings/view_listings.html", context)


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
