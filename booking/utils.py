from listings.models import ListingSlot
import datetime as dt


def subtract_interval(slot_start, slot_end, booking_start, booking_end):
    """
    Given an availability interval [slot_start, slot_end) and a booking interval
    [booking_start, booking_end), subtract the booking interval and return a list
    of resulting intervals.
    """
    # If no overlap, return the original interval.
    if booking_end <= slot_start or booking_start >= slot_end:
        return [(slot_start, slot_end)]

    intervals = []
    # Left remainder (if booking starts after slot_start)
    if booking_start > slot_start:
        intervals.append((slot_start, min(booking_start, slot_end)))
    # Right remainder (if booking ends before slot_end)
    if booking_end < slot_end:
        intervals.append((max(booking_end, slot_start), slot_end))
    return intervals


def merge_intervals(intervals):
    """
    Given a list of intervals (tuples of (start, end)), merge overlapping or adjacent
    intervals and return a new list.
    """
    if not intervals:
        return []
    # Sort by start time.
    intervals.sort(key=lambda iv: iv[0])
    merged = [intervals[0]]
    for current in intervals[1:]:
        last = merged[-1]
        # If current interval overlaps or is adjacent to last, merge them.
        if current[0] <= last[1]:
            merged[-1] = (last[0], max(last[1], current[1]))
        else:
            merged.append(current)
    return merged


def block_out_booking(listing, booking):
    """
    For an approved booking, subtract each booking interval from the listing’s available
    slots and update the ListingSlot records.
    """
    # 1. Get current availability intervals from ListingSlot records.
    current_intervals = []
    for slot in listing.slots.all():
        start_dt = dt.datetime.combine(slot.start_date, slot.start_time)
        end_dt = dt.datetime.combine(slot.end_date, slot.end_time)
        current_intervals.append((start_dt, end_dt))

    # 2. For each BookingSlot in this booking, subtract its interval.
    for booking_slot in booking.slots.all():
        b_start = dt.datetime.combine(booking_slot.start_date, booking_slot.start_time)
        b_end = dt.datetime.combine(booking_slot.end_date, booking_slot.end_time)
        new_intervals = []
        for interval in current_intervals:
            new_intervals.extend(
                subtract_interval(interval[0], interval[1], b_start, b_end)
            )
        current_intervals = new_intervals

    # 3. Merge intervals (in case adjacent intervals now exist).
    new_availability = merge_intervals(current_intervals)

    # 4. Update the database:
    # Delete existing ListingSlot records for this listing.
    listing.slots.all().delete()
    # Create new ListingSlot records based on new_availability.
    for start_dt, end_dt in new_availability:
        ListingSlot.objects.create(
            listing=listing,
            start_date=start_dt.date(),
            start_time=start_dt.time(),
            end_date=end_dt.date(),
            end_time=end_dt.time(),
        )


def restore_booking_availability(listing, booking):
    """
    When a booking is canceled or declined, add back its intervals to the listing’s
    availability and merge with any existing intervals.
    """
    # 1. Get current availability intervals.
    current_intervals = []
    for slot in listing.slots.all():
        start_dt = dt.datetime.combine(slot.start_date, slot.start_time)
        end_dt = dt.datetime.combine(slot.end_date, slot.end_time)
        current_intervals.append((start_dt, end_dt))

    # 2. Get the intervals from the booking that are to be restored.
    restore_intervals = []
    for booking_slot in booking.slots.all():
        b_start = dt.datetime.combine(booking_slot.start_date, booking_slot.start_time)
        b_end = dt.datetime.combine(booking_slot.end_date, booking_slot.end_time)
        restore_intervals.append((b_start, b_end))

    # 3. Combine current intervals with the restored intervals.
    combined = current_intervals + restore_intervals
    merged_intervals = merge_intervals(combined)

    # 4. Update the ListingSlot records.
    listing.slots.all().delete()
    for start_dt, end_dt in merged_intervals:
        ListingSlot.objects.create(
            listing=listing,
            start_date=start_dt.date(),
            start_time=start_dt.time(),
            end_date=end_dt.date(),
            end_time=end_dt.time(),
        )
