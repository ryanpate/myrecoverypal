from django import forms
from .models import JournalEntry, Milestone

class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['title', 'content', 'mood', 'prompt', 'tags', 'is_private']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
            'mood': forms.Select(choices=[(i, f'{i}/10') for i in range(1, 11)]),
            'tags': forms.TextInput(attrs={'placeholder': 'gratitude, progress, challenges'}),
        }

class MilestoneForm(forms.ModelForm):
    class Meta:
        model = Milestone
        fields = ['title', 'description', 'date_achieved']
        widgets = {
            'date_achieved': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }