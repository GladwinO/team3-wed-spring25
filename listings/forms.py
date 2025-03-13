from django import forms
from django.forms import inlineformset_factory
from .models import Listing, ListingSlot, Review

HALF_HOUR_CHOICES = [
    (f"{hour:02d}:{minute:02d}", f"{hour:02d}:{minute:02d}")
    for hour in range(24)
    for minute in (0, 30)
]


# 1. ListingForm: For basic listing details.
class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = ["title", "location", "rent_per_hour", "description"]


# 2. ListingSlotForm: For each availability interval.
class ListingSlotForm(forms.ModelForm):
    start_time = forms.ChoiceField(choices=HALF_HOUR_CHOICES)
    end_time = forms.ChoiceField(choices=HALF_HOUR_CHOICES)

    class Meta:
        model = ListingSlot
        fields = ["start_date", "start_time", "end_date", "end_time"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        start_time = cleaned_data.get("start_time")
        end_date = cleaned_data.get("end_date")
        end_time = cleaned_data.get("end_time")

        if start_date and end_date and start_date > end_date:
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


def validate_non_overlapping_slots(formset):
    """
    Prevent overlapping availability slots within the same listing.
    This simple check compares the string representations;
    for more robust checks, consider converting to datetime objects.
    """
    intervals = []
    for form in formset:
        if form.cleaned_data.get("DELETE"):
            continue  # Skip forms marked for deletion.
        start_date = form.cleaned_data.get("start_date")
        start_time = form.cleaned_data.get("start_time")
        end_date = form.cleaned_data.get("end_date")
        end_time = form.cleaned_data.get("end_time")
        if start_date and start_time and end_date and end_time:
            start_dt = f"{start_date} {start_time}"
            end_dt = f"{end_date} {end_time}"
            for existing_start, existing_end in intervals:
                # If not completely before or after, they overlap.
                if not (end_dt <= existing_start or start_dt >= existing_end):
                    raise forms.ValidationError("Availability slots cannot overlap.")
            intervals.append((start_dt, end_dt))


ListingSlotFormSet = inlineformset_factory(
    Listing, ListingSlot, form=ListingSlotForm, extra=1, can_delete=True
)


# 3. ReviewForm: For reviewing a listing.
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
