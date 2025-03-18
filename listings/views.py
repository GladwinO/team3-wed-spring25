# listings/views.py
from datetime import datetime, timedelta, time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from .forms import ListingForm, ListingSlotFormSet, validate_non_overlapping_slots
from .models import Listing

# Define half-hour choices for use in the search form
HALF_HOUR_CHOICES = [
    (f"{hour:02d}:{minute:02d}", f"{hour:02d}:{minute:02d}")
    for hour in range(24)
    for minute in (0, 30)
]


@login_required
def create_listing(request):
    if request.method == "POST":
        listing_form = ListingForm(request.POST)
        slot_formset = ListingSlotFormSet(request.POST, prefix="form")
        if listing_form.is_valid() and slot_formset.is_valid():
            try:
                validate_non_overlapping_slots(slot_formset)
            except Exception:  # catches ValidationError from our custom validator
                messages.error(request, "Overlapping slots detected. Please correct.")
                return render(
                    request,
                    "listings/create_listing.html",
                    {"form": listing_form, "slot_formset": slot_formset},
                )
            new_listing = listing_form.save(commit=False)
            new_listing.user = request.user
            new_listing.save()
            slot_formset.instance = new_listing
            slot_formset.save()
            messages.success(request, "Listing created successfully!")
            return redirect("view_listings")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        listing_form = ListingForm()
        slot_formset = ListingSlotFormSet(prefix="form")
    return render(
        request,
        "listings/create_listing.html",
        {"form": listing_form, "slot_formset": slot_formset},
    )


@login_required
def edit_listing(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id, user=request.user)
    if request.method == "POST":
        listing_form = ListingForm(request.POST, instance=listing)
        slot_formset = ListingSlotFormSet(request.POST, instance=listing, prefix="form")
        if listing_form.is_valid() and slot_formset.is_valid():
            listing_form.save()
            slot_formset.save()
            return redirect("manage_listings")
    else:
        listing_form = ListingForm(instance=listing)
        slot_formset = ListingSlotFormSet(instance=listing, prefix="form")
    return render(
        request,
        "listings/edit_listing.html",
        {"form": listing_form, "slot_formset": slot_formset, "listing": listing},
    )


def simplify_location(location_string):
    """
    Simplifies a location string before sending to template.
    Example: "Tandon School of Engineering, Johnson Street, Downtown Brooklyn, Brooklyn..."
    becomes "Tandon School of Engineering, Brooklyn"
    """
    if not location_string:
        return ""

    parts = [part.strip() for part in location_string.split(",")]
    if len(parts) < 2:
        return location_string

    building = parts[0]

    # Find the city (Brooklyn, Manhattan, etc.)
    city = next(
        (
            part
            for part in parts
            if part.strip()
            in ["Brooklyn", "Manhattan", "Queens", "Bronx", "Staten Island"]
        ),
        "New York",
    )

    # For educational institutions, keep the full name
    if any(
        term in building.lower()
        for term in ["school", "university", "college", "institute"]
    ):
        return f"{building}, {city}"

    # For other locations, use first two parts
    street = parts[1]
    return f"{building}, {street}, {city}"


def view_listings(request):
    all_listings = Listing.objects.all()

    # Extract common filter parameters
    max_price = request.GET.get("max_price")
    filter_type = request.GET.get("filter_type", "single")  # "single" or "multiple"

    # Filter by price if provided
    if max_price:
        try:
            max_price_val = float(max_price)
            all_listings = all_listings.filter(rent_per_hour__lte=max_price_val)
        except ValueError:
            pass

    # Error messages list for displaying in template
    error_messages = []
    warning_messages = []

    # Apply availability filters
    if filter_type == "single":
        # Single continuous interval filter
        start_date = request.GET.get("start_date")  # e.g., "2025-03-12"
        end_date = request.GET.get("end_date")  # e.g., "2025-03-12"
        start_time = request.GET.get("start_time")
        end_time = request.GET.get("end_time")
        if start_date and end_date and start_time and end_time:
            try:
                user_start_str = f"{start_date} {start_time}"  # "2025-03-12 10:00"
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
        # Multiple intervals filter.
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
                # The listing must be available for every requested interval.
                available_for_all = True
                for s_dt, e_dt in intervals:
                    if not listing.is_available_for_range(s_dt, e_dt):
                        available_for_all = False
                        break
                if available_for_all:
                    filtered.append(listing)
            all_listings = filtered

    elif filter_type == "recurring":
        # Extract recurring filter parameters
        r_start_date = request.GET.get("recurring_start_date")
        r_start_time = request.GET.get("recurring_start_time")
        r_end_time = request.GET.get("recurring_end_time")
        pattern = request.GET.get("recurring_pattern", "daily")
        overnight = request.GET.get("recurring_overnight") == "on"

        # Flag to track if we should apply filter
        continue_with_filter = True

        # Check that all required fields are provided
        if r_start_date and r_start_time and r_end_time:
            try:
                intervals = []
                start_date = datetime.strptime(r_start_date, "%Y-%m-%d").date()

                # Validate start time < end time unless overnight is checked
                s_time = datetime.strptime(r_start_time, "%H:%M").time()
                e_time = datetime.strptime(r_end_time, "%H:%M").time()
                if s_time >= e_time and not overnight:
                    error_messages.append(
                        "Start time must be before end time unless overnight booking is selected"
                    )
                    continue_with_filter = False

                if pattern == "daily":
                    # Daily pattern requires an end date
                    r_end_date = request.GET.get("recurring_end_date")
                    if not r_end_date:
                        error_messages.append(
                            "End date is required for daily recurring pattern"
                        )
                        continue_with_filter = False
                    else:
                        end_date = datetime.strptime(r_end_date, "%Y-%m-%d").date()

                        # Validate end date is after start date
                        if end_date < start_date:
                            error_messages.append(
                                "End date must be on or after start date"
                            )
                            continue_with_filter = False
                        else:
                            days_count = (end_date - start_date).days + 1

                            # Just a warning, but no enforced cap
                            if days_count > 90:
                                warning_messages.append(
                                    "Daily recurring pattern spans over 90 days, results may be limited"
                                )

                            if continue_with_filter:
                                for day_offset in range(days_count):
                                    current_date = start_date + timedelta(
                                        days=day_offset
                                    )
                                    s_dt = datetime.combine(current_date, s_time)

                                    # If overnight, end time is on the next day
                                    end_date = current_date + timedelta(
                                        days=1 if overnight else 0
                                    )
                                    e_dt = datetime.combine(end_date, e_time)

                                    intervals.append((s_dt, e_dt))

                elif pattern == "weekly":
                    # Weekly pattern requires number of weeks
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
                                    current_date = start_date + timedelta(
                                        weeks=week_offset
                                    )
                                    s_dt = datetime.combine(current_date, s_time)

                                    # If overnight, end time is on the next day
                                    end_date = current_date + timedelta(
                                        days=1 if overnight else 0
                                    )
                                    e_dt = datetime.combine(end_date, e_time)

                                    intervals.append((s_dt, e_dt))
                    except ValueError:
                        error_messages.append("Invalid number of weeks")
                        continue_with_filter = False

                # Filter listings that are available for all the recurring intervals
                if continue_with_filter and intervals:
                    filtered = []
                    for listing in all_listings:
                        available_for_all = True
                        for s_dt, e_dt in intervals:
                            # For overnight bookings, we need to check both days
                            if overnight and s_time >= e_time:
                                # Check if listing has slots for both the evening and morning parts
                                evening_available = listing.is_available_for_range(
                                    s_dt, datetime.combine(s_dt.date(), time(23, 59))
                                )
                                morning_available = listing.is_available_for_range(
                                    datetime.combine(e_dt.date(), time(0, 0)), e_dt
                                )
                                if not (evening_available and morning_available):
                                    available_for_all = False
                                    break
                            # Normal case - use existing method
                            elif not listing.is_available_for_range(s_dt, e_dt):
                                available_for_all = False
                                break
                        if available_for_all:
                            filtered.append(listing)
                    all_listings = filtered

            except ValueError:
                error_messages.append("Invalid date or time format")

    # Add extra display information to each listing BEFORE pagination
    if isinstance(all_listings, list):
        # For already filtered lists, sort them by ID
        all_listings.sort(key=lambda x: x.id)
    else:
        # For querysets, add ordering
        all_listings = all_listings.order_by("id")

    # Process each listing to add display information
    processed_listings = []
    for listing in all_listings:
        # Get and simplify location name
        location_full = listing.location.split("[")[0].strip()
        listing.location_name = simplify_location(location_full)

        # Add average rating
        listing.avg_rating = listing.average_rating()
        listing.rating_count = listing.rating_count()

        # Add earliest/latest dates and times
        try:
            listing.available_from = listing.slots.earliest(
                "start_date", "start_time"
            ).start_date
            listing.available_until = listing.slots.latest(
                "end_date", "end_time"
            ).end_date
            listing.available_time_until = listing.slots.earliest(
                "start_time"
            ).start_time
            listing.available_time_from = listing.slots.latest("end_time").end_time
        except listing.slots.model.DoesNotExist:
            # Set default values if no slots exist
            listing.available_from = None
            listing.available_until = None
            listing.available_time_from = None
            listing.available_time_until = None

        processed_listings.append(listing)

    # Now paginate the processed listings
    page_number = request.GET.get("page", 1)
    paginator = Paginator(processed_listings, 25)  # Show 25 listings per page
    page_obj = paginator.get_page(page_number)

    # Create context
    context = {
        "listings": page_obj,
        "half_hour_choices": HALF_HOUR_CHOICES,
        "filter_type": filter_type,
        # Pass along single-interval filter fields
        "max_price": max_price or "",
        "start_date": request.GET.get("start_date", ""),
        "end_date": request.GET.get("end_date", ""),
        "start_time": request.GET.get("start_time", ""),
        "end_time": request.GET.get("end_time", ""),
        # For multiple intervals, also pass the interval_count and the individual interval fields as needed.
        "interval_count": request.GET.get("interval_count", "0"),
        # Add recurring filter parameters
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
    }

    # Handle AJAX requests for "Load More"
    if request.GET.get("ajax") == "1":
        return render(request, "listings/partials/listing_cards.html", context)

    # Normal full page render
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

    # Check for pending or approved bookings
    active_bookings = listing.booking_set.filter(status__in=["PENDING", "APPROVED"])
    if active_bookings.exists():
        # Re-run the manage_listings logic to attach pending_bookings & approved_bookings
        owner_listings = Listing.objects.filter(user=request.user)
        for lst in owner_listings:
            lst.pending_bookings = lst.booking_set.filter(status="PENDING")
            lst.approved_bookings = lst.booking_set.filter(status="APPROVED")

        return render(
            request,
            "listings/manage_listings.html",
            {
                "listings": owner_listings,
                "delete_error": "Cannot delete listing with pending or approved bookings. \
                Please handle those bookings first.",
                "error_listing_id": listing_id,
            },
        )

    # If no active bookings, proceed with normal delete
    if request.method == "POST":
        listing.delete()
        return redirect("manage_listings")

    return render(request, "listings/confirm_delete.html", {"listing": listing})


def listing_reviews(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    reviews = listing.reviews.all()  # using the related_name set in the Review model
    return render(
        request,
        "listings/listing_reviews.html",
        {"listing": listing, "reviews": reviews},
    )
