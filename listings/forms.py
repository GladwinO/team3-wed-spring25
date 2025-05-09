from django import forms
from django.forms import inlineformset_factory
from datetime import datetime
from .models import (
    Listing,
    ListingSlot,
    Review,
    PARKING_SPOT_SIZES,
)  # Import the constant

HALF_HOUR_CHOICES = [
    (f"{hour:02d}:{minute:02d}", f"{hour:02d}:{minute:02d}")
    for hour in range(24)
    for minute in (0, 30)
]


# 1. ListingForm: For basic listing details.
class ListingForm(forms.ModelForm):
    # Make each field explicitly required with custom error messages
    title = forms.CharField(
        required=True,
        error_messages={"required": "Please enter a spot title"},
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    description = forms.CharField(
        required=True,
        error_messages={"required": "Please provide a description of your spot"},
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 5}),
    )

    location = forms.CharField(
        required=True,
        error_messages={"required": "Please select a location on the map"},
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    rent_per_hour = forms.DecimalField(
        required=True,
        min_value=0.01,
        error_messages={
            "required": "Please enter the price per hour",
            "min_value": "Price must be greater than zero",
            "invalid": "Please enter a valid price",
        },
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    parking_spot_size = forms.ChoiceField(
        choices=PARKING_SPOT_SIZES,
        initial="STANDARD",
        required=True,
        error_messages={"required": "Please select a parking spot size"},
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Select the type of vehicle your parking spot can accommodate",
    )

    # Add this field to provide time choices to the form
    time_choices = forms.ChoiceField(
        choices=HALF_HOUR_CHOICES, required=False, widget=forms.HiddenInput()
    )

    class Meta:
        model = Listing
        fields = [
            "title",
            "location",
            "rent_per_hour",
            "description",
            "parking_spot_size",  # Add the new field
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

            # Don't disable fields - just visually disable them
            # This ensures their values are preserved when submitted
            if not self.initial.get("has_ev_charger", False):
                self.fields["charger_level"].widget.attrs[
                    "style"
                ] = "opacity: 0.6; pointer-events: none;"
                self.fields["connector_type"].widget.attrs[
                    "style"
                ] = "opacity: 0.6; pointer-events: none;"

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

    def clean_rent_per_hour(self):
        rent_per_hour = self.cleaned_data.get("rent_per_hour")
        if rent_per_hour <= 0:
            raise forms.ValidationError("Price per hour must be greater than 0.")
        return rent_per_hour

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Double-check the clearing of fields
        if not instance.has_ev_charger:
            instance.charger_level = ""
            instance.connector_type = ""

        if commit:
            instance.save()
        return instance


# Add this class after your ListingForm class


# Form for recurring listing creation
class RecurringListingForm(forms.Form):
    recurring_start_date = forms.DateField(
        required=True,
        error_messages={"required": "Start date is required"},
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
                "min": datetime.today().date().strftime("%Y-%m-%d"),
            }
        ),
    )

    recurring_end_date = forms.DateField(
        required=False,  # Conditionally required based on pattern
        error_messages={"required": "End date is required for daily pattern"},
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
                "min": datetime.today().date().strftime("%Y-%m-%d"),
            }
        ),
    )

    recurring_start_time = forms.ChoiceField(
        choices=HALF_HOUR_CHOICES,
        required=True,
        error_messages={"required": "Start time is required"},
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    recurring_end_time = forms.ChoiceField(
        choices=HALF_HOUR_CHOICES,
        required=True,
        error_messages={"required": "End time is required"},
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    recurring_overnight = forms.BooleanField(required=False)

    recurring_pattern = forms.ChoiceField(
        choices=[("daily", "Daily"), ("weekly", "Weekly")],
        required=True,
        error_messages={"required": "Please select a recurring pattern"},
        widget=forms.RadioSelect(),
    )

    recurring_weeks = forms.IntegerField(
        required=False,  # Conditionally required based on pattern
        min_value=1,
        max_value=52,
        initial=4,
        error_messages={
            "required": "Number of weeks is required for weekly pattern",
            "min_value": "Number of weeks must be at least 1",
            "max_value": "Number of weeks cannot exceed 52",
        },
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        pattern = cleaned_data.get("recurring_pattern")
        start_date = cleaned_data.get("recurring_start_date")
        end_date = cleaned_data.get("recurring_end_date")
        start_time = cleaned_data.get("recurring_start_time")
        end_time = cleaned_data.get("recurring_end_time")
        is_overnight = cleaned_data.get("recurring_overnight", False)

        # Today's date for comparisons
        today = datetime.today()
        if hasattr(today, "date"):
            today = today.date()
        current_time = datetime.now().time()

        # Start date must not be in the past
        if start_date and start_date < today:
            self.add_error("recurring_start_date", "Start date cannot be in the past.")

        # Keep your existing validation for daily pattern
        if pattern == "daily":
            # End date is required for daily pattern
            if not end_date:
                self.add_error(
                    "recurring_end_date", "End date is required for daily pattern"
                )

            # Add the additional validations for end date
            elif end_date:
                # End date must not be in the past
                if end_date < today:
                    self.add_error(
                        "recurring_end_date", "End date cannot be in the past."
                    )

                # Start date must be before or equal to end date
                if start_date and start_date > end_date:
                    self.add_error(
                        "recurring_end_date", "End date cannot be before start date."
                    )

        elif pattern == "weekly":
            # Keep your existing validation for weekly pattern
            weeks = cleaned_data.get("recurring_weeks")
            if not weeks:
                self.add_error(
                    "recurring_weeks", "Number of weeks is required for weekly pattern"
                )

        # Time validation
        if start_time and end_time:
            st = (
                datetime.strptime(start_time, "%H:%M").time()
                if isinstance(start_time, str)
                else start_time
            )
            et = (
                datetime.strptime(end_time, "%H:%M").time()
                if isinstance(end_time, str)
                else end_time
            )

            # If not overnight, end time must be after start time
            if st >= et and not is_overnight:
                self.add_error(
                    "recurring_end_time",
                    "End time must be later than start time unless overnight is selected.",
                )

            # If date is today, times must be in the future
            if start_date and start_date == today:
                if st <= current_time:
                    self.add_error(
                        "recurring_start_time",
                        "Start time cannot be in the past for today's date.",
                    )
                if et <= current_time and not is_overnight:
                    self.add_error(
                        "recurring_end_time",
                        "End time cannot be in the past for today's date.",
                    )

        return cleaned_data


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

        # Today's date for comparisons
        today = datetime.today().date()

        # Start date must not be in the past
        if start_date and start_date < today:
            self.add_error("start_date", "Start date cannot be in the past.")

        # End date must not be in the past
        if end_date and end_date < today:
            self.add_error("end_date", "End date cannot be in the past.")

        if start_date and end_date:
            # Keep your existing validation but convert to field-specific errors
            if start_date > end_date:
                self.add_error("end_date", "End date cannot be before start date.")

            if start_date == end_date and start_time and end_time:
                st = datetime.strptime(start_time, "%H:%M").time()
                et = datetime.strptime(end_time, "%H:%M").time()
                if st >= et:
                    self.add_error(
                        "end_time",
                        "End time must be later than start time on the same day.",
                    )

            # Keep your existing validation for new timeslots
            if start_date == today and start_time:
                if not self.instance.pk:  # i.e. newly added slot
                    current_time = datetime.now().time()
                    st = datetime.strptime(start_time, "%H:%M").time()
                    if st <= current_time:
                        self.add_error(
                            "start_time",
                            "Start time cannot be in the past for today's date.",
                        )

                # Also validate end time for today
                if end_date == today and end_time:
                    if not self.instance.pk:  # i.e. newly added slot
                        current_time = datetime.now().time()
                        et = datetime.strptime(end_time, "%H:%M").time()
                        if et <= current_time:
                            self.add_error(
                                "end_time",
                                "End time cannot be in the past for today's date.",
                            )

        return cleaned_data


def validate_non_overlapping_slots(formset):
    """
    Prevent overlapping availability slots within the same listing.
    Instead of raising an exception, adds errors to the relevant form fields.
    Returns True if no overlaps found, False otherwise.
    """
    intervals = []
    has_overlap = False

    # First pass: collect intervals
    valid_forms = []
    for form in formset:
        # Skip forms marked for deletion.
        if form.cleaned_data.get("DELETE"):
            continue
        start_date = form.cleaned_data.get("start_date")
        start_time = form.cleaned_data.get("start_time")
        end_date = form.cleaned_data.get("end_date")
        end_time = form.cleaned_data.get("end_time")
        if start_date and start_time and end_date and end_time:
            st = (
                datetime.strptime(start_time, "%H:%M").time()
                if isinstance(start_time, str)
                else start_time
            )
            et = (
                datetime.strptime(end_time, "%H:%M").time()
                if isinstance(end_time, str)
                else end_time
            )
            start_dt = datetime.combine(start_date, st)
            end_dt = datetime.combine(end_date, et)
            valid_forms.append((form, start_dt, end_dt))
            intervals.append((start_dt, end_dt))

    # Second pass: check for overlaps
    for i, (form, start_dt, end_dt) in enumerate(valid_forms):
        for j, (other_start, other_end) in enumerate(intervals):
            # Skip comparing with itself
            if j == i:
                continue

            # Check for overlap
            if not (end_dt <= other_start or start_dt >= other_end):
                # Add error to the relevant fields
                form.add_error("start_date", "This slot overlaps with another slot")
                form.add_error("end_date", "This slot overlaps with another slot")
                has_overlap = True

    return not has_overlap


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
