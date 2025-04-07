from django import forms
from django.forms import inlineformset_factory
from datetime import datetime
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
        fields = [
            "title",
            "location",
            "rent_per_hour",
            "description",
            "has_ev_charger",
            "charger_level",
            "connector_type",
        ]

    def __init__(self, *args, **kwargs):
        super(ListingForm, self).__init__(*args, **kwargs)
        # If this is an existing listing, disable editing for "location"
        if self.instance and self.instance.pk:
            self.fields["location"].disabled = True

        # Only attempt to modify EV fields if they exist
        if (
            "has_ev_charger" in self.fields
            and "charger_level" in self.fields
            and "connector_type" in self.fields
        ):
            # Make charger_level and connector_type dependent on has_ev_charger
            self.fields["charger_level"].widget.attrs[
                "class"
            ] = "ev-charger-option form-select"
            self.fields["connector_type"].widget.attrs[
                "class"
            ] = "ev-charger-option form-select"

            # If initial has_ev_charger is False, disable the other fields
            if not self.initial.get("has_ev_charger", False):
                self.fields["charger_level"].widget.attrs["disabled"] = "disabled"
                self.fields["connector_type"].widget.attrs["disabled"] = "disabled"

    def clean(self):
        cleaned_data = super().clean()
        has_ev_charger = cleaned_data.get("has_ev_charger")

        if not has_ev_charger:
            # Explicitly set empty strings instead of using defaults
            cleaned_data["charger_level"] = ""
            cleaned_data["connector_type"] = ""
        elif has_ev_charger:
            # Validate required fields when charger is enabled
            charger_level = cleaned_data.get("charger_level")
            connector_type = cleaned_data.get("connector_type")

            if not charger_level:
                self.add_error(
                    "charger_level",
                    "Charger level is required when EV charger is available",
                )

            if not connector_type:
                self.add_error(
                    "connector_type",
                    "Connector type is required when EV charger is available",
                )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Double-check the clearing of fields
        if not instance.has_ev_charger:
            instance.charger_level = ""
            instance.connector_type = ""

        if commit:
            instance.save()
        return instance


# 2. ListingSlotForm: For each availability interval.
class ListingSlotForm(forms.ModelForm):
    start_time = forms.ChoiceField(choices=HALF_HOUR_CHOICES)
    end_time = forms.ChoiceField(choices=HALF_HOUR_CHOICES)

    class Meta:
        model = ListingSlot
        fields = ["start_date", "start_time", "end_date", "end_time"]
        widgets = {
            "start_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "min": datetime.today().date().strftime("%Y-%m-%d"),
                }
            ),
            "end_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "min": datetime.today().date().strftime("%Y-%m-%d"),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.start_time:
                self.initial["start_time"] = self.instance.start_time.strftime("%H:%M")
            if self.instance.end_time:
                self.initial["end_time"] = self.instance.end_time.strftime("%H:%M")

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        start_time = cleaned_data.get("start_time")
        end_date = cleaned_data.get("end_date")
        end_time = cleaned_data.get("end_time")

        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError("Start date cannot be after end date.")

            if start_date == end_date and start_time and end_time:
                st = datetime.strptime(start_time, "%H:%M").time()
                et = datetime.strptime(end_time, "%H:%M").time()
                if st >= et:
                    raise forms.ValidationError(
                        "End time must be later than start time on the same day."
                    )

            # Only enforce the "start time in the past" rule for new timeslots
            today = datetime.today().date()
            if start_date == today and start_time:
                if not self.instance.pk:  # i.e. newly added slot
                    current_time = datetime.now().time()
                    st = datetime.strptime(start_time, "%H:%M").time()
                    if st <= current_time:
                        raise forms.ValidationError(
                            "Start time cannot be in the past for today's date."
                        )
        return cleaned_data


def validate_non_overlapping_slots(formset):
    """
    Prevent overlapping availability slots within the same listing.
    This version converts the string times to datetime objects to
    accurately compare intervals.
    """
    intervals = []
    for form in formset:
        # Skip forms marked for deletion.
        if form.cleaned_data.get("DELETE"):
            continue
        start_date = form.cleaned_data.get("start_date")
        start_time = form.cleaned_data.get("start_time")
        end_date = form.cleaned_data.get("end_date")
        end_time = form.cleaned_data.get("end_time")
        if start_date and start_time and end_date and end_time:
            st = datetime.strptime(start_time, "%H:%M").time()
            et = datetime.strptime(end_time, "%H:%M").time()
            start_dt = datetime.combine(start_date, st)
            end_dt = datetime.combine(end_date, et)
            for existing_start, existing_end in intervals:
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
