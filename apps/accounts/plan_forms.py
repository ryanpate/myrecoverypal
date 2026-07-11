"""Form for the relapse prevention plan builder."""
from django import forms

from apps.accounts.plan_models import RelapsePreventionPlan

MAX_CONTACTS = 10
MAX_VALUE_LEN = 100
CONTACT_KEYS = ('name', 'phone', 'relationship')

SECTION_PLACEHOLDERS = {
    'triggers': "e.g. payday Fridays, my brother's house, feeling left out, boredom after 9pm…",
    'warning_signs': "e.g. skipping meetings, 'just one won't hurt' thoughts, isolating, poor sleep…",
    'coping_strategies': "e.g. call Sam, 4-7-8 breathing, leave the situation, hit the Craving SOS page…",
    'reasons': "e.g. my kids, my health, the person I'm becoming, mornings without shame…",
    'emergency_steps': "e.g. 1) leave, 2) call sponsor, 3) open Craving SOS, 4) if unsafe call 988…",
    'halt_notes': "e.g. anger sneaks up at work; loneliness on Sunday nights; keep snacks in the car…",
}


class RelapsePreventionPlanForm(forms.ModelForm):
    class Meta:
        model = RelapsePreventionPlan
        fields = [
            'triggers', 'warning_signs', 'coping_strategies',
            'reasons', 'emergency_steps', 'halt_notes',
            'support_contacts',
        ]
        widgets = {
            **{
                f: forms.Textarea(attrs={
                    'rows': 4,
                    'class': 'form-control',
                    'placeholder': SECTION_PLACEHOLDERS[f],
                })
                for f in RelapsePreventionPlan.SECTION_FIELDS
            },
            # JS-managed rows serialize into this hidden JSON field;
            # Django's JSONField form field decodes the string for us.
            'support_contacts': forms.HiddenInput(),
        }

    def clean_support_contacts(self):
        value = self.cleaned_data.get('support_contacts') or []
        if not isinstance(value, list):
            raise forms.ValidationError("Contacts must be a list.")
        cleaned = []
        for row in value:
            if not isinstance(row, dict):
                raise forms.ValidationError("Each contact must be an object.")
            contact = {
                key: str(row.get(key, '')).strip()[:MAX_VALUE_LEN]
                for key in CONTACT_KEYS
            }
            if any(contact.values()):
                cleaned.append(contact)
        if len(cleaned) > MAX_CONTACTS:
            raise forms.ValidationError(
                f"Please keep it to {MAX_CONTACTS} contacts or fewer.")
        return cleaned
