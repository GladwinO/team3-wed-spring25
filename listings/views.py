# listings/views.py

from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ListingForm
from .models import Listing


@login_required
def create_listing(request):
    if request.method == 'POST':
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.user = request.user
            listing.save()
            messages.success(request, 'Listing created successfully!')
            return redirect('view_listings')
        else:
            print(form.errors)
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ListingForm()

    return render(request, 'listings/create_listing.html', {
        'form': form,
    })


def view_listings(request):
    all_listings = Listing.objects.all()

    # Extract GET paramters
    max_price = request.GET.get('max_price')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    start_time = request.GET.get('start_time')
    end_time = request.GET.get('end_time')

    # Apply filters if parameters are provided
    if max_price:
        try:
            max_price = float(max_price)
            all_listings = all_listings.filter(rent_per_hour__lte=max_price)
        except ValueError:
            pass

    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            all_listings = all_listings.filter(
                available_from__lte=start_date, available_until__gte=start_date)
            # The listing must start on or after the availbe_from
            # and end before or on the end date.
        except ValueError:
            pass

    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            all_listings = all_listings.filter(
                available_from__lte=end_date, available_until__gte=end_date)
            # The listing must start on or after the availbe_from
            # and end before or on the end date.
        except ValueError:
            pass

    if start_date and end_date:
        if start_date > end_date:
            # No listings should appear if start date is after end date.
            all_listings = all_listings.none()

    if start_time:
        try:
            start_time = datetime.strptime(start_time, '%H:%M').time()
            all_listings = all_listings.filter(
                available_time_from__lte=start_time, available_time_until__gte=start_time)
            # The listing must start on or after the availbe_from
            # and end before or on the end time
        except ValueError:
            pass

    if end_time:
        try:
            end_time = datetime.strptime(end_time, '%H:%M').time()
            all_listings = all_listings.filter(
                available_time_until__gte=end_time, available_time_from__lte=end_time)
            # The listing must start on or after the availbe_from
            # and end before or on the end time
        except ValueError:
            pass

    if start_time and end_time:
        if start_time > end_time:
            all_listings = all_listings.none()

    return render(request, 'listings/view_listings.html', {'listings': all_listings})


def manage_listings(request):
    owner_listings = Listing.objects.filter(user=request.user)
    return render(request, 'listings/manage_listings.html', {'listings': owner_listings})


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

    return render(request, 'listings/edit_listing.html', {'form': form})


@login_required
def delete_listing(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id, user=request.user)
    if request.method == 'POST':
        listing.delete()
        return redirect('manage_listings')

    return render(request, 'listings/confirm_delete.html', {'listing': listing})
