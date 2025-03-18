from django.test import TestCase
from django import forms
from listings.forms import validate_non_overlapping_slots
import datetime


class MockForm:
    def __init__(self, cleaned_data):
        self.cleaned_data = cleaned_data


class TestValidateNonOverlappingSlots(TestCase):
    def test_non_overlapping_slots_pass_validation(self):
        """Test that non-overlapping slots pass validation."""
        formset = [
            MockForm(
                {
                    "start_date": datetime.date(2023, 1, 1),
                    "start_time": "09:00",
                    "end_date": datetime.date(2023, 1, 1),
                    "end_time": "12:00",
                }
            ),
            MockForm(
                {
                    "start_date": datetime.date(2023, 1, 1),
                    "start_time": "13:00",
                    "end_date": datetime.date(2023, 1, 1),
                    "end_time": "15:00",
                }
            ),
            MockForm(
                {
                    "start_date": datetime.date(2023, 1, 2),
                    "start_time": "09:00",
                    "end_date": datetime.date(2023, 1, 2),
                    "end_time": "12:00",
                }
            ),
        ]

        # Should not raise an exception
        validate_non_overlapping_slots(formset)

    def test_adjacent_slots_pass_validation(self):
        """Test that adjacent slots (one ends when another begins) pass validation."""
        formset = [
            MockForm(
                {
                    "start_date": datetime.date(2023, 1, 1),
                    "start_time": "09:00",
                    "end_date": datetime.date(2023, 1, 1),
                    "end_time": "12:00",
                }
            ),
            MockForm(
                {
                    "start_date": datetime.date(2023, 1, 1),
                    "start_time": "12:00",
                    "end_date": datetime.date(2023, 1, 1),
                    "end_time": "15:00",
                }
            ),
        ]

        # Should not raise an exception
        validate_non_overlapping_slots(formset)

    def test_overlapping_slots_fail_validation(self):
        """Test that overlapping slots fail validation."""
        formset = [
            MockForm(
                {
                    "start_date": datetime.date(2023, 1, 1),
                    "start_time": "09:00",
                    "end_date": datetime.date(2023, 1, 1),
                    "end_time": "12:00",
                }
            ),
            MockForm(
                {
                    "start_date": datetime.date(2023, 1, 1),
                    "start_time": "11:00",
                    "end_date": datetime.date(2023, 1, 1),
                    "end_time": "14:00",
                }
            ),
        ]

        # Should raise ValidationError
        with self.assertRaises(forms.ValidationError):
            validate_non_overlapping_slots(formset)

    def test_overlapping_across_days_fail_validation(self):
        """Test that slots overlapping across days fail validation."""
        formset = [
            MockForm(
                {
                    "start_date": datetime.date(2023, 1, 1),
                    "start_time": "20:00",
                    "end_date": datetime.date(2023, 1, 2),
                    "end_time": "10:00",
                }
            ),
            MockForm(
                {
                    "start_date": datetime.date(2023, 1, 2),
                    "start_time": "09:00",
                    "end_date": datetime.date(2023, 1, 2),
                    "end_time": "12:00",
                }
            ),
        ]

        # Should raise ValidationError
        with self.assertRaises(forms.ValidationError):
            validate_non_overlapping_slots(formset)

    def test_deleted_form_ignored(self):
        """Test that forms marked for deletion are ignored in validation."""
        formset = [
            MockForm(
                {
                    "start_date": datetime.date(2023, 1, 1),
                    "start_time": "09:00",
                    "end_date": datetime.date(2023, 1, 1),
                    "end_time": "12:00",
                }
            ),
            MockForm(
                {
                    "start_date": datetime.date(2023, 1, 1),
                    "start_time": "11:00",
                    "end_date": datetime.date(2023, 1, 1),
                    "end_time": "14:00",
                    "DELETE": True,  # This form should be ignored
                }
            ),
        ]

        # Should not raise an exception because the overlapping form is marked for deletion
        validate_non_overlapping_slots(formset)

    def test_incomplete_form_data_handled(self):
        """Test that forms with missing fields don't cause errors."""
        formset = [
            MockForm(
                {
                    "start_date": datetime.date(2023, 1, 1),
                    "start_time": "09:00",
                    "end_date": datetime.date(2023, 1, 1),
                    "end_time": "12:00",
                }
            ),
            MockForm(
                {
                    "start_date": datetime.date(2023, 1, 1),
                    # Missing start_time
                    "end_date": datetime.date(2023, 1, 1),
                    "end_time": "14:00",
                }
            ),
        ]

        # Should not raise an exception as incomplete forms are skipped
        validate_non_overlapping_slots(formset)
