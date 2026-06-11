from django import forms
from apps.accounts.supporter_models import PRESET_CHOICES


class SupporterInviteForm(forms.Form):
    invite_email = forms.EmailField()
    preset = forms.ChoiceField(choices=PRESET_CHOICES, initial='standard')


class PresetForm(forms.Form):
    preset = forms.ChoiceField(choices=PRESET_CHOICES)
