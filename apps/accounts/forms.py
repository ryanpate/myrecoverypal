from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Milestone, SupportMessage

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text='Required. Enter a valid email address.')
    sobriety_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Optional. You can add this later.'
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'sobriety_date')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'bio', 'location',
            'sobriety_date', 'recovery_goals', 'avatar',
            'is_profile_public', 'show_sobriety_date', 'allow_messages',
            'email_notifications', 'newsletter_subscriber', 'is_sponsor'
        ]
        widgets = {
            'sobriety_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'recovery_goals': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }
        help_texts = {
            'bio': 'Tell the community about yourself (max 500 characters)',
            'location': 'City, State or Country',
            'sobriety_date': 'The date you began your recovery journey',
            'recovery_goals': 'What are you working towards in your recovery?',
            'is_sponsor': 'Check this if you\'re available to sponsor others',
            'is_profile_public': 'Allow other members to view your profile',
            'show_sobriety_date': 'Display your sobriety date on your public profile',
            'allow_messages': 'Allow other members to send you private messages',
            'email_notifications': 'Receive email notifications for messages and milestones',
            'newsletter_subscriber': 'Receive our weekly recovery newsletter',
        }
        
class MilestoneForm(forms.ModelForm):
    class Meta:
        model = Milestone
        fields = ['title', 'description', 'date_achieved', 'milestone_type']
        widgets = {
            'date_achieved': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class SupportMessageForm(forms.ModelForm):
    class Meta:
        model = SupportMessage
        fields = ['subject', 'message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 5}),
        }