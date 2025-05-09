import datetime as dt

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Max, Min, Q, F
from django.utils import timezone

# extract coordinates from location string
from .utils import extract_coordinates

from .utils import simplify_location

EV_CHARGER_LEVELS = [
    ("L1", "Level 1 (120V)"),
    ("L2", "Level 2 (240V)"),
    ("L3", "Level 3 (DC Fast Charging)"),
]

EV_CONNECTOR_TYPES = [
    ("J1772", "J1772 (Standard)"),
    ("CCS", "CCS (Combined Charging System)"),
    ("CHAdeMO", "CHAdeMO"),
    ("TESLA", "Tesla"),
    ("TYPE2", "Type 2 (European)"),
    ("OTHER", "Other"),
]

PARKING_SPOT_SIZES = [
    ("STANDARD", "Standard Size"),
    ("COMPACT", "Compact"),
    ("OVERSIZE", "Large/Oversize"),
    ("COMMERCIAL", "Truck/Commercial"),
]


class Listing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    rent_per_hour = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def location_name(self):
        """Returns a simplified version of the location string."""
        return simplify_location(self.location)

    @property
    def latitude(self):
        """Returns the latitude of the listing."""
        return extract_coordinates(self.location)[0]

    @property
    def longitude(self):
        """Returns the longitude of the listing."""
        return extract_coordinates(self.location)[1]

    @property
    def avg_rating(self):
        """Returns the average rating for this listing."""
        reviews = self.reviews.all()
        if reviews:
            return sum(review.rating for review in reviews) / reviews.count()
        return None

    @property
    def rating_count(self):
        """Returns the total number of reviews for this listing."""
        return self.reviews.count()

    def __str__(self):
        return f"{self.title} - {self.location}"

    def is_available_for_range(self, start_dt, end_dt):
        """
        Return True if this listing's combined ListingSlot intervals
        cover the entire range [start_dt, end_dt).
        """
        # Debug output
        # print(f"\nChecking availability for: {start_dt} to {end_dt}")

        # Ensure input datetimes are timezone-aware
        if timezone.is_naive(start_dt):
            start_dt = timezone.make_aware(start_dt)
        if timezone.is_naive(end_dt):
            end_dt = timezone.make_aware(end_dt)

        # # Output all available slots for debugging
        # print(f"Available slots for listing #{self.id} ({self.title}):")
        # for slot in self.slots.all():
        #     slot_start = dt.datetime.combine(slot.start_date, slot.start_time)
        #     slot_end = dt.datetime.combine(slot.end_date, slot.end_time)
        #     if timezone.is_naive(slot_start):
        #         slot_start = timezone.make_aware(slot_start)
        #     if timezone.is_naive(slot_end):
        #         slot_end = timezone.make_aware(slot_end)
        #     print(f"  - {slot_start} to {slot_end}")

        intervals = []
        for slot in self.slots.all():
            # Create timezone-aware slot datetimes
            slot_start = dt.datetime.combine(slot.start_date, slot.start_time)
            slot_end = dt.datetime.combine(slot.end_date, slot.end_time)

            # Make timezone-aware
            if timezone.is_naive(slot_start):
                slot_start = timezone.make_aware(slot_start)
            if timezone.is_naive(slot_end):
                slot_end = timezone.make_aware(slot_end)

            intervals.append((slot_start, slot_end))

        intervals.sort(key=lambda iv: iv[0])
        merged = []
        for interval in intervals:
            if not merged:
                merged.append(interval)
            else:
                last_start, last_end = merged[-1]
                this_start, this_end = interval
                if this_start <= last_end:
                    merged[-1] = (last_start, max(last_end, this_end))
                else:
                    merged.append(interval)

        # # Debug the merged intervals
        # print("Merged intervals:")
        # for iv_start, iv_end in merged:
        #     print(f"  - {iv_start} to {iv_end}")

        # FIX: Modified logic to specifically check if any interval contains the request
        # Check if any single interval fully contains our booking request
        for iv_start, iv_end in merged:
            if iv_start <= start_dt and iv_end >= end_dt:
                # print(f"✓ Found containing interval: {iv_start} to {iv_end}")
                return True

        # If no single interval contains our request, use the original algorithm
        coverage_start = start_dt
        for iv_start, iv_end in merged:
            # print(f"Checking if {iv_start}-{iv_end} advances coverage from {coverage_start}")
            if iv_start <= coverage_start and iv_end >= end_dt:
                # print("✓ Interval covers remaining range")
                return True
            if iv_start > coverage_start:
                # print(f"✗ Gap in coverage between {coverage_start} and {iv_start}")
                return False
            coverage_start = iv_end

        result = coverage_start >= end_dt
        # print(f"Final coverage check: {coverage_start} >= {end_dt} = {result}")
        return result

    # These two properties allow us to access the start and end date and time of a listing
    @property
    def earliest_start_datetime(self):
        """Returns the earliest start date and time from all slots."""
        # First find the earliest date
        earliest_date = self.slots.aggregate(earliest_date=Min("start_date"))[
            "earliest_date"
        ]
        if not earliest_date:
            return None

        # Then among slots with that date, find the earliest time
        earliest_time = self.slots.filter(start_date=earliest_date).aggregate(
            earliest_time=Min("start_time")
        )["earliest_time"]

        return dt.datetime.combine(earliest_date, earliest_time)

    @property
    def latest_end_datetime(self):
        """Returns the latest end date and time from all slots."""
        # First find the latest date
        latest_date = self.slots.aggregate(latest_date=Max("end_date"))["latest_date"]
        if not latest_date:
            return None

        # Then among slots with that date, find the latest time
        latest_time = self.slots.filter(end_date=latest_date).aggregate(
            latest_time=Max("end_time")
        )["latest_time"]

        return dt.datetime.combine(latest_date, latest_time)

    has_ev_charger = models.BooleanField(default=False, verbose_name="Has EV Charger")
    charger_level = models.CharField(
        max_length=10,
        choices=EV_CHARGER_LEVELS,
        default="L2",  # Default to Level 2 as it's most common
        blank=True,
        verbose_name="EV Charger Level",
    )
    connector_type = models.CharField(
        max_length=10,
        choices=EV_CONNECTOR_TYPES,
        default="J1772",  # Default to the standard connector
        blank=True,
        verbose_name="EV Connector Type",
    )
    parking_spot_size = models.CharField(
        max_length=15,
        choices=PARKING_SPOT_SIZES,
        default="STANDARD",  # Default to standard size
        verbose_name="Parking Spot Size",
    )

    def has_availability_after_date(self, date):
        """Check if listing has any availability on or after the specified date"""
        # Find slots where:
        # 1. Start date is less than or equal to the provided date (slot has started)
        # 2. End date is greater than or equal to the provided date (slot continues past this date)
        return self.slots.filter(start_date__lte=date, end_date__gte=date).exists()

    def has_availability_before_date(self, date):
        """Check if listing has any availability on or before the specified date"""
        # Filter slots where:
        # 1. Start date is less than the provided date (slot starts before this date)
        # 2. End date is greater than or equal to the provided date (slot continues at least until this date)
        return self.slots.filter(start_date__lte=date, end_date__gte=date).exists()

    def has_availability_after_time(self, time_obj):
        """Check if listing has any slot available at or after the specified time"""
        return self.slots.filter(
            # Multi-day slot with time after or equal to start time on first day
            Q(start_date__lt=F("end_date"), start_time__lte=time_obj)
            |
            # Multi-day slot with time before end time on last day
            Q(start_date__lt=F("end_date"), end_time__gt=time_obj)
            |
            # Middle days of multi-day slots (always available)
            Q(start_date__lt=F("end_date"))
            & ~Q(start_date=F("start_date"))
            & ~Q(end_date=F("end_date"))
            |
            # Same-day slot with the requested time in range
            Q(start_date=F("end_date"), start_time__lte=time_obj, end_time__gt=time_obj)
        ).exists()

    def has_availability_before_time(self, time_obj):
        """Check if listing has any availability before the specified time"""
        return self.slots.filter(
            # Multi-day slot with time before or at start time on first day
            Q(start_date__lt=F("end_date"), start_time__lt=time_obj)
            |
            # Multi-day slot with time at or after end time on last day
            Q(start_date__lt=F("end_date"), end_time__gte=time_obj)
            |
            # Middle days of multi-day slots (always available)
            Q(start_date__lt=F("end_date"))
            & ~Q(start_date=F("start_date"))
            & ~Q(end_date=F("end_date"))
            |
            # Same-day slot with the requested time in range
            Q(start_date=F("end_date"), start_time__lt=time_obj, end_time__gte=time_obj)
        ).exists()


class ListingSlot(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="slots")
    start_date = models.DateField()
    start_time = models.TimeField()
    end_date = models.DateField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.listing.title} slot: {self.start_date} {self.start_time} - {self.end_date} {self.end_time}"


class Review(models.Model):
    # Use a one-to-one relation to Booking so that each booking gets one review
    booking = models.OneToOneField(
        "booking.Booking", on_delete=models.CASCADE, related_name="review"
    )
    # Redundant but handy: directly link to the listing being reviewed
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # For the star rating (e.g. 1 to 5)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(max_length=1000, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.listing.title} by {self.user.username}"


class BookmarkedListing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookmarks")
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="bookmarked_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "listing")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} bookmarked {self.listing.title}"
