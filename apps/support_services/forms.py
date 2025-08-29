# apps/support_services/forms.py

from django import forms
from django.core.validators import RegexValidator
from .models import Meeting, SupportService


class MeetingSubmissionForm(forms.Form):
    """Form for submitting a new meeting"""
    
    # Basic Information
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Morning Serenity Group'
        }),
        help_text='Enter a descriptive name for the meeting'
    )
    
    group = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Rochester Recovery Group'
        }),
        help_text='Optional: Name of the parent group'
    )
    
    # Schedule
    day = forms.ChoiceField(
        choices=[('', '-- Select Day --')] + Meeting.DAY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time'
        }),
        help_text='Meeting start time'
    )
    
    end_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time'
        }),
        help_text='Optional: Meeting end time'
    )
    
    # Location
    attendance_option = forms.ChoiceField(
        choices=Meeting.ATTENDANCE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='in_person'
    )
    
    location = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., First Methodist Church'
        }),
        help_text='Name of the venue or building'
    )
    
    address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 123 Main Street'
        })
    )
    
    city = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Rochester'
        })
    )
    
    state = forms.CharField(
        max_length=2,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., IL',
            'maxlength': '2',
            'style': 'text-transform: uppercase;'
        }),
        validators=[
            RegexValidator(r'^[A-Z]{2}$', 'Enter a valid 2-letter state code')
        ]
    )
    
    postal_code = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 62563'
        })
    )
    
    # Online Meeting Info
    conference_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., https://zoom.us/j/123456789'
        }),
        help_text='Online meeting link (Zoom, Google Meet, etc.)'
    )
    
    conference_url_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'e.g., Meeting ID: 123 456 789, Passcode: serenity'
        }),
        help_text='Instructions for joining online'
    )
    
    conference_phone = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., +1-312-626-6799'
        }),
        help_text='Phone number for dial-in option'
    )
    
    # Meeting Types
    types = forms.MultipleChoiceField(
        choices=Meeting.MEETING_TYPES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text='Select all that apply'
    )
    
    # Contact Information
    website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://www.example.org'
        })
    )
    
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'contact@example.org'
        })
    )
    
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '217-555-0100'
        })
    )
    
    # 7th Tradition
    venmo = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '@GroupName'
        }),
        help_text='Venmo handle for 7th Tradition contributions'
    )
    
    paypal = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'GroupName'
        }),
        help_text='PayPal.me username'
    )
    
    square = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '$GroupName'
        }),
        help_text='Square Cash App cashtag'
    )
    
    # Additional Info
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'e.g., Wheelchair accessible, Large print materials available, Childcare provided'
        }),
        help_text='Any additional information about the meeting'
    )
    
    # Contact for submission
    contact_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com'
        }),
        help_text='Your email (for verification purposes only)'
    )
    
    contact_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your phone number'
        }),
        help_text='Optional: Your phone number'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        attendance = cleaned_data.get('attendance_option')
        
        # Validate based on attendance option
        if attendance in ['in_person', 'hybrid']:
            if not cleaned_data.get('location') and not cleaned_data.get('address'):
                raise forms.ValidationError(
                    'Physical location or address is required for in-person meetings'
                )
        
        if attendance in ['online', 'hybrid']:
            if not cleaned_data.get('conference_url') and not cleaned_data.get('conference_phone'):
                raise forms.ValidationError(
                    'Online meeting URL or phone number is required for online meetings'
                )
        
        # Ensure at least one schedule option
        if not cleaned_data.get('day') and not cleaned_data.get('time'):
            if attendance != 'online':  # Online meetings might be 24/7
                raise forms.ValidationError(
                    'Please provide meeting day and/or time'
                )
        
        return cleaned_data


class SupportServiceSubmissionForm(forms.Form):
    """Form for submitting a new support service"""
    
    # Basic Information
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Springfield Recovery Center'
        })
    )
    
    type = forms.ChoiceField(
        choices=SupportService.SERVICE_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    category = forms.ChoiceField(
        choices=SupportService.CATEGORY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='local'
    )
    
    organization = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Parent organization (if applicable)'
        })
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Provide a brief description of the service'
        })
    )
    
    # Contact Information
    phone = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '1-800-000-0000'
        })
    )
    
    phone_display = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '1-800-HELP (4357)'
        }),
        help_text='Optional: Formatted phone number for display'
    )
    
    text_support = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Text HELP to 12345'
        })
    )
    
    website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://www.example.org'
        })
    )
    
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'info@example.org'
        })
    )
    
    chat_support = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://www.example.org/chat'
        }),
        help_text='Link to online chat support'
    )
    
    # Location (for physical facilities)
    address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '789 Recovery Way'
        })
    )
    
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Springfield'
        })
    )
    
    state = forms.CharField(
        max_length=2,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'IL',
            'maxlength': '2',
            'style': 'text-transform: uppercase;'
        })
    )
    
    postal_code = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '62704'
        })
    )
    
    # Service Details
    hours = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 24/7/365 or Mon-Fri 8am-6pm'
        })
    )
    
    languages = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'English, Spanish, French'
        }),
        help_text='Languages supported (comma-separated)'
    )
    
    services_offered = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'List services offered (one per line)'
        }),
        help_text='e.g., Crisis counseling, Referrals, etc.'
    )
    
    cost = forms.ChoiceField(
        choices=SupportService.COST_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='unknown'
    )
    
    insurance_accepted = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Medicare, Medicaid, Private insurance'
        }),
        help_text='List accepted insurance (one per line)'
    )
    
    specializations = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Alcohol addiction, Drug addiction, Dual diagnosis'
        }),
        help_text='Areas of specialization (one per line)'
    )
    
    # Formats
    formats = forms.MultipleChoiceField(
        choices=[
            ('in-person', 'In-Person'),
            ('online', 'Online'),
            ('hybrid', 'Hybrid'),
            ('phone', 'Phone'),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text='Service delivery formats'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        service_type = cleaned_data.get('type')
        
        # Validate based on service type
        if service_type == 'treatment_facility':
            if not cleaned_data.get('address'):
                raise forms.ValidationError(
                    'Address is required for treatment facilities'
                )
        
        if service_type == 'helpline':
            if not cleaned_data.get('phone') and not cleaned_data.get('text_support'):
                raise forms.ValidationError(
                    'Phone number or text support is required for helplines'
                )
        
        # Process multi-line fields into lists
        if cleaned_data.get('languages'):
            cleaned_data['languages'] = [
                lang.strip() 
                for lang in cleaned_data['languages'].split(',') 
                if lang.strip()
            ]
        
        if cleaned_data.get('services_offered'):
            cleaned_data['services'] = [
                service.strip() 
                for service in cleaned_data['services_offered'].split('\n') 
                if service.strip()
            ]
            del cleaned_data['services_offered']
        
        if cleaned_data.get('insurance_accepted'):
            cleaned_data['insurance_accepted'] = [
                ins.strip() 
                for ins in cleaned_data['insurance_accepted'].split('\n') 
                if ins.strip()
            ]
        
        if cleaned_data.get('specializations'):
            cleaned_data['specializations'] = [
                spec.strip() 
                for spec in cleaned_data['specializations'].split('\n') 
                if spec.strip()
            ]
        
        return cleaned_data