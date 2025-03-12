# listings/views.py
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ListingForm
from .models import Listing


@login_required
def create_listing(request):
    if request.method == "POST":
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.user = request.user
            listing.save()
            messages.success(request, "Listing created successfully!")
            return redirect("view_listings")
        else:
            print(form.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        form = ListingForm()

    return render(
        request,
        "listings/create_listing.html",
        {
            "form": form,
        },
    )


def view_listings(request):
    # Get current date and time
    now = datetime.now()
    today = now.date()
    current_time = now.time()

    # Start with listings where available_until is in the future
    all_listings = Listing.objects.filter(available_until__gt=today)

    # For listings ending today, ensure the time hasn't passed
    today_listings = Listing.objects.filter(
        available_until=today, available_time_until__gt=current_time
    )

    # Combine the two querysets
    all_listings = all_listings | today_listings

    # Extract GET parameters
    max_price = request.GET.get("max_price")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    start_time = request.GET.get("start_time")
    end_time = request.GET.get("end_time")

    # Apply filters if parameters are provided
    if max_price:
        try:
            max_price = float(max_price)
            all_listings = all_listings.filter(rent_per_hour__lte=max_price)
        except ValueError:
            pass

    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            all_listings = all_listings.filter(
                available_from__lte=start_date_obj,
                available_until__gte=start_date_obj,
            )
        except ValueError:
            pass

    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
            all_listings = all_listings.filter(
                available_from__lte=end_date_obj,
                available_until__gte=end_date_obj,
            )
        except ValueError:
            pass

    if start_date and end_date:
        if start_date > end_date:
            all_listings = all_listings.none()

    if start_time:
        try:
            start_time_obj = datetime.strptime(start_time, "%H:%M").time()
            all_listings = all_listings.filter(
                available_time_from__lte=start_time_obj,
                available_time_until__gte=start_time_obj,
            )
        except ValueError:
            pass

    if end_time:
        try:
            end_time_obj = datetime.strptime(end_time, "%H:%M").time()
            all_listings = all_listings.filter(
                available_time_from__lte=end_time_obj,
                available_time_until__gte=end_time_obj,
            )
        except ValueError:
            pass

    if start_time and end_time:
        try:
            start_time_obj = datetime.strptime(start_time, "%H:%M").time()
            end_time_obj = datetime.strptime(end_time, "%H:%M").time()
            if start_time_obj > end_time_obj:
                all_listings = all_listings.none()
        except ValueError:
            pass

    # Add average rating to each listing
    for listing in all_listings:
        print("listing", listing)

        listing.location_name = listing.location.split("[")[0].strip()
        print("listing average rating", listing.average_rating())
        listing.avg_rating = listing.average_rating()
        listing.lol = 5

    # Build half-hour choices for the dropdowns
    half_hour_choices = []
    for hour in range(24):
        for minute in (0, 30):
            half_hour_choices.append(f"{hour:02d}:{minute:02d}")

    context = {
        "listings": all_listings,
        "half_hour_choices": half_hour_choices,
    }
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
def edit_listing(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id, user=request.user)
    if request.method == "POST":
        form = ListingForm(request.POST, instance=listing)
        if form.is_valid():
            form.save()
            return redirect("manage_listings")
    else:
        form = ListingForm(instance=listing)

    return render(request, "listings/edit_listing.html", {"form": form})


@login_required
def delete_listing(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id, user=request.user)

    # Check for pending or approved bookings
    active_bookings = listing.booking_set.filter(status__in=["PENDING", "APPROVED"])

    if active_bookings.exists():
        # Instead of using messages, return directly to manage_listings with an error
        return render(
            request,
            "listings/manage_listings.html",
            {
                "listings": Listing.objects.filter(user=request.user),
                "delete_error": """Cannot delete listing with pending or approved bookings.
                Please handle those bookings first.""",
                "error_listing_id": listing_id,  # To highlight which listing has the error
            },
        )

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
