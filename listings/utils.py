from datetime import datetime


def is_booking_slot_covered(booking_slot, intervals):
    """
    Check if the given booking slot is completely covered by at least one interval.

    :param booking_slot: A booking slot instance with attributes start_date, start_time, end_date, end_time.
    :param intervals: A list of tuples (start_dt, end_dt) where each is a datetime object.
    :return: True if the booking slot is fully within one of the intervals, otherwise False.
    """
    booking_start = datetime.combine(booking_slot.start_date, booking_slot.start_time)
    booking_end = datetime.combine(booking_slot.end_date, booking_slot.end_time)

    for iv_start, iv_end in intervals:
        if iv_start <= booking_start and iv_end >= booking_end:
            return True
    return False


def is_booking_covered_by_intervals(booking, intervals):
    """
    Check if every slot in the booking is completely covered by one of the intervals.

    :param booking: A booking instance with related slots accessible via booking.slots.all()
    :param intervals: A list of tuples (start_dt, end_dt) representing new availability intervals.
    :return: True if all booking slots are fully covered, otherwise False.
    """
    for slot in booking.slots.all():
        if not is_booking_slot_covered(slot, intervals):
            return False
    return True
