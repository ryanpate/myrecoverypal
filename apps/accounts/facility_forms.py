"""Forms for self-serve facility onboarding."""
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class FacilitySignupForm(forms.Form):
    facility_name = forms.CharField(max_length=200)
    contact_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField()
    password = forms.CharField(min_length=8, widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'An account with this email already exists. '
                'Log in and contact us to add a facility.')
        return email
