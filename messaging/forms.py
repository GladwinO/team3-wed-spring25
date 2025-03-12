from django import forms
from django.contrib.auth.models import User
from .models import Message


class MessageForm(forms.ModelForm):
    recipient = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={"class": "form-select"}),
        required=True,
    )
    subject = forms.CharField(
        required=False, widget=forms.TextInput(attrs={"class": "form-control"})
    )
    body = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}), required=True
    )

    class Meta:
        model = Message
        fields = ["recipient", "subject", "body"]
