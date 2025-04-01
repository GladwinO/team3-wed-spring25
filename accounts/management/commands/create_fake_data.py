import random
from datetime import date, datetime, time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from accounts.utilities import get_valid_nyc_coordinate
from booking.models import Booking, BookingSlot
from listings.models import Listing, ListingSlot, Review

# Import block_out_booking so that approved bookings subtract availability.
from booking.utils import block_out_booking


class Command(BaseCommand):
    help = "Create fake data: 10 users, 100 listings, 200 bookings, and 100 reviews"

    def handle(self, *args, **kwargs):
        # Check if fake data exists by verifying the existence of "user1"
        if User.objects.filter(username="user1").exists():
            self.stdout.write("Existing fake data found. Deleting...")

            # Delete all users created by this script (user1 through user10)
            for i in range(1, 11):
                username = f"user{i}"
                User.objects.filter(username=username).delete()

            self.stdout.write(self.style.SUCCESS("Existing fake data deleted."))

        # Continue with creating new fake data...
        fake = Faker()
        users = []

        # Create 10 users with password "testdata"
        self.stdout.write("Creating users...")
        for i in range(1, 11):
            username = f"user{i}"
            email = f"{username}@example.com"
            user, created = User.objects.get_or_create(
                username=username, defaults={"email": email}
            )
            user.set_password("testdata")
            user.save()
            users.append(user)
            self.stdout.write(self.style.SUCCESS(f"User created: {username}"))

        # Create 100 listings with valid NYC coordinates
        self.stdout.write("Creating listings...")
        listings = []
        for i in range(1, 101):
            user = random.choice(users)
            title = f"Listing #{i}"

            # Generate valid NYC coordinates
            latitude, longitude = get_valid_nyc_coordinate()
            location = f"Sample Location {i} [{latitude},{longitude}]"

            rent_per_hour = round(random.uniform(10.00, 50.00), 2)
            description = fake.text(max_nb_chars=200)
            listing = Listing.objects.create(
                user=user,
                title=title,
                location=location,
                rent_per_hour=rent_per_hour,
                description=description,
            )
            listings.append(listing)
            self.stdout.write(
                self.style.SUCCESS(f"Listing created: {title} at {location}")
            )

        # Create ListingSlots for each listing (1 to 3 slots per listing)
        self.stdout.write("Creating listing slots...")
        for listing in listings:
            num_slots = random.randint(1, 3)
            for _ in range(num_slots):
                # Choose a random start_date from today to 30 days ahead
                start_date_obj = date.today() + timedelta(days=random.randint(0, 30))
                # Determine duration: 0 for same-day, or 1-3 days for a multi-day slot.
                duration_days = random.randint(0, 3)
                end_date_obj = start_date_obj + timedelta(days=duration_days)

                if duration_days == 0:
                    # Same-day slot: choose a start time between 6:00 and 16:00 (in minutes)
                    start_minutes = random.choice(range(360, 960, 30))
                    # End time must be at least 30 minutes after start, up to 22:00 (1320 minutes)
                    possible_end_minutes = [
                        m for m in range(start_minutes + 30, 1320, 30)
                    ]
                    if not possible_end_minutes:
                        continue
                    end_minutes = random.choice(possible_end_minutes)
                else:
                    # Multi-day slot: use a morning start and an evening end.
                    start_minutes = random.choice(range(360, 721, 30))  # 6:00 to 12:00
                    end_minutes = random.choice(range(960, 1320, 30))  # 16:00 to 22:00

                st_time = time(hour=start_minutes // 60, minute=start_minutes % 60)
                et_time = time(hour=end_minutes // 60, minute=end_minutes % 60)

                listing_slot = ListingSlot.objects.create(
                    listing=listing,
                    start_date=start_date_obj,
                    start_time=st_time,
                    end_date=end_date_obj,
                    end_time=et_time,
                )
                listing_slot.listing = listing
                self.stdout.write(
                    self.style.SUCCESS(
                        f"ListingSlot for {listing.title}: {start_date_obj} {st_time} - {end_date_obj} {et_time}"
                    )
                )

        # Create 200 bookings linking users and listings
        self.stdout.write("Creating bookings...")
        bookings = []
        status_choices = ["PENDING", "APPROVED", "DECLINED"]
        for i in range(1, 201):
            user = random.choice(users)
            listing = random.choice(listings)
            email = "no-email@example.com"
            total_price = round(random.uniform(20.00, 500.00), 2)
            status = random.choice(status_choices)
            booking = Booking.objects.create(
                user=user,
                listing=listing,
                email=email,
                total_price=total_price,
                status=status,
            )
            bookings.append(booking)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Booking #{booking.pk} for listing '{listing.title}' created."
                )
            )

        # Create BookingSlots for each booking (1 slot per booking)
        self.stdout.write("Creating booking slots...")
        for booking in bookings:
            listing = booking.listing
            listing_slots = list(listing.slots.all())
            if not listing_slots:
                continue
            chosen_slot = random.choice(listing_slots)
            # Compute listing slot start and end datetimes
            listing_start_dt = datetime.combine(
                chosen_slot.start_date, chosen_slot.start_time
            )
            listing_end_dt = datetime.combine(
                chosen_slot.end_date, chosen_slot.end_time
            )
            total_minutes = int(
                (listing_end_dt - listing_start_dt).total_seconds() // 60
            )
            if total_minutes < 30:
                continue

            # Choose a random start offset in 30-minute increments
            max_offset_slots = (
                total_minutes // 30 - 1
            )  # ensure at least one slot is available
            if max_offset_slots < 0:
                max_offset_slots = 0
            start_offset = random.randint(0, max_offset_slots) * 30
            booking_start_dt = listing_start_dt + timedelta(minutes=start_offset)

            # Choose a duration (in half-hour increments) that fits within the listing slot
            remaining_minutes = total_minutes - start_offset
            possible_durations = [
                30 * i for i in range(1, (remaining_minutes // 30) + 1)
            ]
            if not possible_durations:
                continue
            duration = random.choice(possible_durations)
            booking_end_dt = booking_start_dt + timedelta(minutes=duration)

            bs_start_date = booking_start_dt.date()
            bs_start_time = booking_start_dt.time().replace(second=0, microsecond=0)
            bs_end_date = booking_end_dt.date()
            bs_end_time = booking_end_dt.time().replace(second=0, microsecond=0)

            booking_slot = BookingSlot.objects.create(
                booking=booking,
                start_date=bs_start_date,
                start_time=bs_start_time,
                end_date=bs_end_date,
                end_time=bs_end_time,
            )
            booking_slot.booking = booking
            self.stdout.write(
                self.style.SUCCESS(
                    f"BookingSlot for Booking \
                        #{booking.pk}: {bs_start_date} {bs_start_time} - {bs_end_date} {bs_end_time}"
                )
            )
            # --- NEW: Subtract booking interval from listing availability if approved ---
            if booking.status == "APPROVED":
                block_out_booking(listing, booking)
            # --- END NEW ---

        # Create 100 reviews for random bookings; each review's created_at is before March 2025.
        self.stdout.write("Creating reviews...")
        review_bookings = random.sample(bookings, 100)
        start_date_dt = datetime(2020, 1, 1)
        end_date_dt = datetime(2025, 3, 1)
        for booking in review_bookings:
            rating = random.randint(1, 5)
            comment = fake.sentence(nb_words=10)
            review = Review.objects.create(
                booking=booking,
                listing=booking.listing,
                user=booking.user,
                rating=rating,
                comment=comment,
            )
            delta = end_date_dt - start_date_dt
            random_seconds = random.randint(0, int(delta.total_seconds()))
            random_date = start_date_dt + timedelta(seconds=random_seconds)
            aware_random_date = timezone.make_aware(
                random_date, timezone.get_default_timezone()
            )
            Review.objects.filter(pk=review.pk).update(created_at=aware_random_date)
            self.stdout.write(
                self.style.SUCCESS(f"Review for Booking #{booking.pk} created.")
            )

        self.stdout.write(self.style.SUCCESS("Fake data creation complete."))
