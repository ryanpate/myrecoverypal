from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, UserProfile

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['bio', 'avatar', 'phone', 'emergency_contact', 
                 'emergency_phone', 'is_public', 'show_sobriety_date', 
                 'allow_messages']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

class SobrietyDateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['sobriety_date', 'recovery_goals']
        widgets = {
            'sobriety_date': forms.DateInput(attrs={'type': 'date'}),
            'recovery_goals': forms.Textarea(attrs={'rows': 4}),
        }