# listings/forms.py
import datetime
import pytz
from django import forms
from django.utils import timezone
from .models import Listing, Review

# Generate half-hour choices for 00:00 -> 23:30
HALF_HOUR_CHOICES = [
    (f"{hour:02d}:{minute:02d}", f"{hour:02d}:{minute:02d}")
    for hour in range(24)
    for minute in (0, 30)
]


class ListingForm(forms.ModelForm):
    # Use ChoiceFields for half-hour increments
    available_time_from = forms.ChoiceField(
        choices=HALF_HOUR_CHOICES,
        label="Available Time From",
    )
    available_time_until = forms.ChoiceField(
        choices=HALF_HOUR_CHOICES,
        label="Available Time Until",
    )

    class Meta:
        model = Listing
        fields = [
            "title",
            "location",
            "rent_per_hour",
            "description",
            "available_from",
            "available_until",
            "available_time_from",
            "available_time_until",
        ]
        widgets = {
            "available_from": forms.DateInput(
                attrs={
                    "type": "date",
                    "min": datetime.date.today().strftime("%Y-%m-%d"),
                }
            ),
            "available_until": forms.DateInput(
                attrs={
                    "type": "date",
                    "min": datetime.date.today().strftime("%Y-%m-%d"),
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        available_from = cleaned_data.get("available_from")
        available_until = cleaned_data.get("available_until")

        # Get current date in NYC timezone
        nyc_tz = pytz.timezone("America/New_York")
        today = timezone.now().astimezone(nyc_tz).date()

        if available_from:
            # Ensure the value is a date object
            if isinstance(available_from, datetime.datetime):
                available_from = available_from.date()

            if available_from < today:
                self.add_error("available_from", "The start date cannot be in the past")

        if available_until:
            # Ensure the value is a date object
            if isinstance(available_until, datetime.datetime):
                available_until = available_until.date()

            if available_until < today:
                self.add_error("available_until", "The end date cannot be in the past")

        if available_from and available_until and available_from > available_until:
            self.add_error(
                "available_until", "The end date must be after the start date"
            )

        # Check rent validation
        rent_per_hour = cleaned_data.get("rent_per_hour")
        if rent_per_hour is not None and rent_per_hour <= 0:
            self.add_error("__all__", "Rent per hour must be a positive number")

        # Check time validation
        time_from_str = cleaned_data.get("available_time_from")  # e.g. '08:00'
        time_until_str = cleaned_data.get("available_time_until")  # e.g. '12:30'
        if time_from_str and time_until_str:
            time_format = "%H:%M"
            time_from = datetime.datetime.strptime(time_from_str, time_format).time()
            time_until = datetime.datetime.strptime(time_until_str, time_format).time()

            # Get current time in NYC
            current_time = timezone.now().astimezone(nyc_tz).time()

            # If listing starts today, check if the start time hasn't already passed
            if available_from == today and time_from <= current_time:
                self.add_error(
                    "available_time_from",
                    "For listings starting today, the start time must be in the future",
                )

            # Only enforce time order if dates are the same
            if available_from and available_until and available_from == available_until:
                if time_from >= time_until:
                    self.add_error(
                        "available_time_until",
                        "When start and end dates are the same, the end time must be after the start time",
                    )

        return cleaned_data


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.NumberInput(
                attrs={"min": 1, "max": 5, "class": "form-control"}
            ),
            "comment": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get("rating")
        if rating < 1 or rating > 5:
            raise forms.ValidationError("Rating must be between 1 and 5")
        return rating
