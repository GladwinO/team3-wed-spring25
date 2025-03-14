# bookings/forms.py
import datetime as dt
from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from .models import Booking, BookingSlot

HALF_HOUR_CHOICES = [
    (f"{hour:02d}:{minute:02d}", f"{hour:02d}:{minute:02d}")
    for hour in range(24)
    for minute in (0, 30)
]


class BookingForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control"}),
        help_text="Enter your email for booking confirmation",
    )

    class Meta:
        model = Booking
        fields = ["email"]


class BookingSlotForm(forms.ModelForm):
    start_time = forms.ChoiceField(choices=HALF_HOUR_CHOICES)
    end_time = forms.ChoiceField(choices=HALF_HOUR_CHOICES)

    class Meta:
        model = BookingSlot
        fields = ["start_date", "start_time", "end_date", "end_time"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        # Pop 'listing' if provided; then store it for later use.
        self.listing = kwargs.pop("listing", None)
        super().__init__(*args, **kwargs)
        # If a booking date exists, filter the time choices based on the listing's slots.
        booking_date_str = self.data.get("start_date") or self.initial.get("start_date")
        if booking_date_str and self.listing:
            try:
                booking_date = dt.datetime.strptime(booking_date_str, "%Y-%m-%d").date()
            except ValueError:
                return
            available_slots = self.listing.slots.filter(
                start_date__lte=booking_date, end_date__gte=booking_date
            )
            valid_times = set()
            for slot in available_slots:
                current_dt = dt.datetime.combine(booking_date, slot.start_time)
                end_dt = dt.datetime.combine(booking_date, slot.end_time)
                while current_dt < end_dt:
                    valid_times.add(current_dt.strftime("%H:%M"))
                    current_dt += dt.timedelta(minutes=30)
            valid_times = sorted(valid_times)
            if valid_times:
                choices = [(t, t) for t in valid_times]
                self.fields["start_time"].choices = choices
                self.fields["end_time"].choices = choices

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        start_time = cleaned_data.get("start_time")
        end_date = cleaned_data.get("end_date")
        end_time = cleaned_data.get("end_time")
        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError("Start date cannot be after end date.")
            if (
                start_date == end_date
                and start_time
                and end_time
                and start_time >= end_time
            ):
                raise forms.ValidationError(
                    "End time must be later than start time on the same day."
                )
        return cleaned_data


class BaseBookingSlotFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        intervals = []
        for form in self.forms:
            if self.can_delete and form.cleaned_data.get("DELETE"):
                continue
            start_date = form.cleaned_data.get("start_date")
            start_time = form.cleaned_data.get("start_time")
            end_date = form.cleaned_data.get("end_date")
            end_time = form.cleaned_data.get("end_time")
            if start_date and start_time and end_date and end_time:
                try:
                    start_dt = dt.datetime.combine(
                        start_date, dt.datetime.strptime(start_time, "%H:%M").time()
                    )
                    end_dt = dt.datetime.combine(
                        end_date, dt.datetime.strptime(end_time, "%H:%M").time()
                    )
                except Exception:
                    raise forms.ValidationError("Invalid time format.")
                for existing_start, existing_end in intervals:
                    if not (end_dt <= existing_start or start_dt >= existing_end):
                        raise forms.ValidationError("Booking intervals cannot overlap.")
                intervals.append((start_dt, end_dt))


BookingSlotFormSet = inlineformset_factory(
    Booking,
    BookingSlot,
    form=BookingSlotForm,
    formset=BaseBookingSlotFormSet,
    extra=1,
    can_delete=True,
)
