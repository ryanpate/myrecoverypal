# apps/accounts/court_forms.py
from django import forms

from apps.accounts.court_models import (
    CourtReportProfile, MeetingAttendance,
)


class CourtReportProfileForm(forms.ModelForm):
    class Meta:
        model = CourtReportProfile
        fields = [
            'legal_name', 'case_number', 'court_name', 'jurisdiction', 'judge_name',
            'probation_officer_name', 'probation_officer_email', 'attorney_email',
            'required_meetings_per_week', 'report_period_start', 'report_period_end',
        ]
        widgets = {
            'report_period_start': forms.DateInput(attrs={'type': 'date'}),
            'report_period_end': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_required_meetings_per_week(self):
        v = self.cleaned_data['required_meetings_per_week']
        if v <= 0:
            raise forms.ValidationError('Must be at least 1 meeting per week.')
        if v > 21:
            raise forms.ValidationError('That seems excessive — courts rarely require more than 7 per week.')
        return v


class MeetingAttendanceForm(forms.ModelForm):
    class Meta:
        model = MeetingAttendance
        fields = [
            'meeting_name', 'meeting_date', 'meeting_end_time',
            'meeting_address', 'meeting_online', 'meeting_platform',
            'program', 'meeting_type', 'verification_method',
            'chair_signature_name', 'notes',
        ]
        widgets = {
            'meeting_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'meeting_end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        data = super().clean()
        if data.get('meeting_online') and not data.get('meeting_platform'):
            self.add_error('meeting_platform', 'Specify the platform (Zoom, online AA, etc.) for online meetings.')
        return data
