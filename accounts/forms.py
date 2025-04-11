from django import forms


class EmailChangeForm(forms.Form):
    email = forms.EmailField(
        label="New Email",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Enter your new email"}
        ),
    )

    def __init__(self, *args, **kwargs):
        # Extract user from kwargs if provided
        self.user = kwargs.pop("user", None)
        super(EmailChangeForm, self).__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"]

        # Check if email is same as current (only when not adding for the first time)
        if self.user and self.user.email and self.user.email == email:
            raise forms.ValidationError(
                "This is already your current email. Please enter a different email address."
            )

        return email
