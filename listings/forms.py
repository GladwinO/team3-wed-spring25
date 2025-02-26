# listings/forms.py
from datetime import timedelta

from django import forms

from .models import Listing


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = ['title', 'location', 'rent_per_hour', 'description',
                  'available_from', 'available_until',
                  'available_time_from', 'available_time_until']
        widgets = {
            'available_from': forms.DateInput(attrs={'type': 'date'}),
            'available_until': forms.DateInput(attrs={'type': 'date'}),
            'available_time_from': forms.TimeInput(attrs={'type': 'time'}),
            'available_time_until': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        errors = []
        # Check date validation
        available_from = cleaned_data.get('available_from')
        available_until = cleaned_data.get('available_until')
        if available_from and available_until and available_from >= available_until:
            errors.append(
                "Available from date must be before available until date")

        # Check rent validation
        rent_per_hour = cleaned_data.get('rent_per_hour')
        if rent_per_hour <= 0:
            errors.append("Rent per hour must be a positive number")

        # Check time validation, TO DO: agree with the team if this form of time validation is correct
        available_time_from = cleaned_data.get('available_time_from')
        available_time_until = cleaned_data.get('available_time_until')
        if available_time_from and available_time_until:
            if available_time_from >= available_time_until:
                errors.append(
                    "Available time from must be before available time until")

            if available_time_from.minute not in [0, 30] or available_time_until.minute not in [0, 30]:
                errors.append(
                    "Available Time From and Available Time Until must start at hour:00 or hour:30")

        if errors:
            raise forms.ValidationError(errors)

        return cleaned_data
