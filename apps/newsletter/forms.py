from django import forms
from .models import Subscriber, Newsletter, NewsletterCategory

class SubscribeForm(forms.ModelForm):
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name (optional)'
        })
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name (optional)'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    
    class Meta:
        model = Subscriber
        fields = ['email', 'first_name', 'last_name']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower()
        return email

class UnsubscribeForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    confirm = forms.BooleanField(
        required=True,
        label='Yes, I want to unsubscribe',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

class NewsletterForm(forms.ModelForm):
    class Meta:
        model = Newsletter
        fields = [
            'title', 'subject', 'preheader', 'category',
            'intro_content', 'main_content',
            'featured_title', 'featured_content', 'featured_link', 'featured_link_text',
            'cta_text', 'cta_url',
            'status', 'scheduled_for'
        ]
        widgets = {
            'intro_content': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'main_content': forms.Textarea(attrs={'rows': 10, 'class': 'form-control rich-editor'}),
            'featured_content': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'scheduled_for': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }

class PreferencesForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(
        queryset=NewsletterCategory.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="I'm interested in:"
    )
    
    class Meta:
        model = Subscriber
        fields = ['frequency', 'categories']
        widgets = {
            'frequency': forms.Select(attrs={'class': 'form-control'}),
        }