# apps/accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import (
    User, Milestone, SupportMessage, SponsorRelationship,
    RecoveryBuddy, RecoveryGroup, GroupMembership, GroupPost,
    GroupChallenge, ChallengeParticipant, ChallengeCheckIn, ChallengeComment
)
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Div, HTML, Field
from crispy_forms.bootstrap import TabHolder, Tab


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True, help_text='Required. Enter a valid email address.')
    sobriety_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Optional. You can add this later.'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1',
                  'password2', 'sobriety_date')

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


class SponsorRequestForm(forms.ModelForm):
    """Form for requesting a sponsor relationship"""

    class Meta:
        model = SponsorRelationship
        fields = ['notes', 'meeting_frequency', 'communication_method']
        widgets = {
            'notes': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Tell them why you would like them as your sponsor...'
            }),
            'meeting_frequency': forms.TextInput(attrs={
                'placeholder': 'e.g., Weekly, Bi-weekly, Monthly'
            }),
            'communication_method': forms.TextInput(attrs={
                'placeholder': 'e.g., Phone calls, Video chat, In-person'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Sponsor Request Details',
                'notes',
                'meeting_frequency',
                'communication_method',
            ),
            Submit('submit', 'Send Sponsor Request',
                   css_class='btn btn-primary')
        )


class RecoveryBuddyForm(forms.ModelForm):
    """Form for requesting a recovery buddy partnership"""

    class Meta:
        model = RecoveryBuddy
        fields = ['check_in_frequency', 'shared_goals']
        widgets = {
            'check_in_frequency': forms.TextInput(attrs={
                'placeholder': 'e.g., Daily, Weekly, As needed'
            }),
            'shared_goals': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'What goals would you like to work on together?'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Recovery Buddy Partnership',
                HTML('<p class="text-muted">Recovery buddies support each other through regular check-ins and shared accountability.</p>'),
                'check_in_frequency',
                'shared_goals',
            ),
            Submit('submit', 'Send Buddy Request', css_class='btn btn-success')
        )


class RecoveryGroupForm(forms.ModelForm):
    """Form for creating recovery groups"""

    class Meta:
        model = RecoveryGroup
        fields = [
            'name', 'description', 'group_type', 'privacy_level',
            'max_members', 'location', 'meeting_schedule',
            'group_image', 'group_color'
        ]
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe the purpose and focus of this group...'
            }),
            'group_type': forms.Select(),
            'privacy_level': forms.Select(),
            'max_members': forms.NumberInput(attrs={
                'min': 2,
                'max': 500,
                'placeholder': 'Leave empty for unlimited'
            }),
            'location': forms.TextInput(attrs={
                'placeholder': 'City, State or Online'
            }),
            'meeting_schedule': forms.TextInput(attrs={
                'placeholder': 'e.g., Tuesdays 7pm EST, First Saturday of month'
            }),
            'group_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            TabHolder(
                Tab(
                    'Basic Info',
                    'name',
                    'description',
                    'group_type',
                    'privacy_level',
                ),
                Tab(
                    'Settings',
                    'max_members',
                    'location',
                    'meeting_schedule',
                ),
                Tab(
                    'Appearance',
                    'group_image',
                    'group_color',
                ),
            ),
            Submit('submit', 'Create Group', css_class='btn btn-primary')
        )

    def clean_name(self):
        name = self.cleaned_data['name']
        if RecoveryGroup.objects.filter(name=name, is_active=True).exists():
            raise ValidationError('A group with this name already exists.')
        return name


class GroupPostForm(forms.ModelForm):
    """Form for creating posts within recovery groups"""

    class Meta:
        model = GroupPost
        fields = ['post_type', 'title', 'content', 'is_anonymous']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'Share your thoughts with the group...'
            }),
            'title': forms.TextInput(attrs={
                'placeholder': 'Give your post a title...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'post_type',
            'title',
            'content',
            Field('is_anonymous', wrapper_class='form-check'),
            Submit('submit', 'Share with Group', css_class='btn btn-primary')
        )


class GroupMembershipForm(forms.ModelForm):
    """Form for managing group memberships"""

    class Meta:
        model = GroupMembership
        fields = ['role_notes']
        widgets = {
            'role_notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Why would you like to join this group?'
            }),
        }


# Challenge System Forms
class GroupChallengeForm(forms.ModelForm):
    """Form for creating group challenges"""

    class Meta:
        model = GroupChallenge
        fields = [
            'title', 'description', 'challenge_type', 'duration_days',
            'start_date', 'daily_goal_description', 'rules_and_guidelines',
            'is_public', 'max_participants', 'allow_buddy_system',
            'enable_leaderboard', 'enable_daily_check_in',
            'completion_badge_name', 'completion_message'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'daily_goal_description': forms.Textarea(attrs={'rows': 3}),
            'rules_and_guidelines': forms.Textarea(attrs={'rows': 3}),
            'completion_message': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            # Limit group choices to groups user is a member of
            self.fields['group'] = forms.ModelChoiceField(
                queryset=user.get_joined_groups(),
                empty_label="Select a group..."
            )


class JoinChallengeForm(forms.ModelForm):
    """Form for joining a challenge"""

    class Meta:
        model = ChallengeParticipant
        fields = ['personal_goal', 'motivation_note']
        widgets = {
            'personal_goal': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'What do you hope to achieve in this challenge?'
            }),
            'motivation_note': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'What motivates you to take on this challenge?'
            }),
        }


class ChallengeCheckInForm(forms.ModelForm):
    """Form for daily challenge check-ins"""

    class Meta:
        model = ChallengeCheckIn
        fields = [
            'completed_daily_goal', 'mood', 'progress_note',
            'custom_metric_1', 'custom_metric_2', 'is_shared_with_group'
        ]
        widgets = {
            'progress_note': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'How did today go? Any challenges or wins?'
            }),
        }

    def __init__(self, challenge=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.challenge = challenge

        # Customize metric labels based on challenge type
        if challenge:
            if challenge.challenge_type == 'exercise':
                self.fields['custom_metric_1'].label = 'Minutes Exercised'
                self.fields['custom_metric_2'].label = 'Intensity (1-10)'
            elif challenge.challenge_type == 'mindfulness':
                self.fields['custom_metric_1'].label = 'Minutes Meditated'
                self.fields['custom_metric_2'].label = 'Mindfulness Rating (1-10)'


class ChallengeCommentForm(forms.ModelForm):
    """Form for commenting on challenge check-ins"""

    class Meta:
        model = ChallengeComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Leave an encouraging comment...'
            }),
        }


class BuddyRequestForm(forms.Form):
    """Form for requesting accountability partner in challenges"""

    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Why would you like to be accountability partners?'
        }),
        required=False
    )


class ChallengeFilterForm(forms.Form):
    """Form for filtering challenges"""

    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(GroupChallenge.STATUS_CHOICES),
        required=False
    )

    challenge_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(GroupChallenge.CHALLENGE_TYPES),
        required=False
    )

    duration = forms.ChoiceField(
        choices=[('', 'Any Duration')] + list(GroupChallenge.DURATION_CHOICES),
        required=False
    )

    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search challenges...'
        })
    )

    my_challenges_only = forms.BooleanField(
        required=False,
        label='My challenges only'
    )


class UserSearchForm(forms.Form):
    """Advanced user search form"""

    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search users...',
            'class': 'form-control'
        })
    )

    location = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Location...'
        })
    )

    is_sponsor = forms.BooleanField(
        required=False,
        label='Sponsors only'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.layout = Layout(
            Div(
                Div('search', css_class='col-md-6'),
                Div('location', css_class='col-md-6'),
                css_class='row'
            ),
            Div(
                Div('is_sponsor', css_class='col-md-6'),
                css_class='row'
            ),
            Submit('submit', 'Search', css_class='btn btn-outline-primary')
        )
