from django import forms
from .models import JournalEntry, JournalReminder


class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = [
            'title', 'content', 'mood_rating',
            'gratitude_1', 'gratitude_2', 'gratitude_3',
            'cravings_today', 'craving_intensity', 'tags'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Give your entry a title (optional)'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Write your thoughts here...'
            }),
            'mood_rating': forms.Select(attrs={'class': 'form-control'}),
            'gratitude_1': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Something you\'re grateful for...'
            }),
            'gratitude_2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Something else you\'re grateful for...'
            }),
            'gratitude_3': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'One more thing you\'re grateful for...'
            }),
            'craving_intensity': forms.Select(attrs={'class': 'form-control'}),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., work, family, progress, challenges'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mood_rating'].empty_label = "How are you feeling? (1-10)"
        self.fields['craving_intensity'].empty_label = "Intensity (if applicable)"

        # Make craving_intensity only required if cravings_today is True
        if self.data.get('cravings_today') == 'on':
            self.fields['craving_intensity'].required = True


class GuidedJournalForm(forms.ModelForm):
    """Form for guided journal entries with a specific prompt"""
    follow_up_1_response = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False
    )
    follow_up_2_response = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = JournalEntry
        fields = ['content', 'mood_rating', 'tags']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
            }),
            'mood_rating': forms.Select(attrs={'class': 'form-control'}),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., progress, challenges, grateful'
            }),
        }


class JournalReminderForm(forms.ModelForm):
    class Meta:
        model = JournalReminder
        fields = ['time', 'monday', 'tuesday', 'wednesday', 'thursday',
                  'friday', 'saturday', 'sunday', 'is_active']
        widgets = {
            'time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control'
            }),
        }
