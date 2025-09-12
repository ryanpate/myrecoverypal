from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Milestone, SupportMessage
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Div, HTML, Field
from crispy_forms.bootstrap import TabHolder, Tab
from django.utils import timezone

from .models import (
    SponsorRelationship, RecoveryBuddy, RecoveryGroup,
    GroupMembership, GroupPost, UserProfile
)

from .models import (
    GroupChallenge, ChallengeParticipant, ChallengeCheckIn,
    ChallengeComment
)

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
            'meeting_frequency': forms.Select(choices=[
                ('', 'Select frequency...'),
                ('weekly', 'Weekly'),
                ('bi-weekly', 'Bi-weekly'),
                ('monthly', 'Monthly'),
                ('as-needed', 'As needed'),
            ]),
            'communication_method': forms.Select(choices=[
                ('', 'Select method...'),
                ('phone', 'Phone calls'),
                ('video', 'Video chat'),
                ('in-person', 'In-person meetings'),
                ('messaging', 'Text messaging'),
                ('mixed', 'Mixed methods'),
            ]),
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
            'check_in_frequency': forms.Select(choices=[
                ('', 'How often would you like to check in?'),
                ('daily', 'Daily'),
                ('weekly', 'Weekly'),
                ('bi-weekly', 'Bi-weekly'),
                ('as-needed', 'As needed'),
            ]),
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


class EnhancedProfileForm(forms.ModelForm):
    """Enhanced profile form with community features"""

    # Add recovery-specific fields
    recovery_stage = forms.ChoiceField(
        choices=[
            ('', 'Select your recovery stage...'),
            ('early', 'Early Recovery (0-90 days)'),
            ('sustained', 'Sustained Recovery (3 months - 1 year)'),
            ('stable', 'Stable Recovery (1-5 years)'),
            ('long-term', 'Long-term Recovery (5+ years)'),
            ('supporter', 'Family/Friend Supporter'),
        ],
        required=False,
        help_text="This helps us connect you with others at similar stages"
    )

    addiction_type = forms.MultipleChoiceField(
        choices=[
            ('alcohol', 'Alcohol'),
            ('opioids', 'Opioids'),
            ('cocaine', 'Cocaine'),
            ('marijuana', 'Marijuana'),
            ('prescription', 'Prescription Drugs'),
            ('gambling', 'Gambling'),
            ('food', 'Food/Eating'),
            ('technology', 'Technology/Gaming'),
            ('other', 'Other'),
        ],
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select all that apply (optional, for better group recommendations)"
    )

    interests = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Hobbies, interests, activities you enjoy...'
        }),
        help_text="Help others find common interests"
    )

    recovery_approach = forms.MultipleChoiceField(
        choices=[
            ('aa', '12-Step Programs (AA, NA, etc.)'),
            ('smart', 'SMART Recovery'),
            ('therapy', 'Individual Therapy'),
            ('group_therapy', 'Group Therapy'),
            ('medication', 'Medication-Assisted Treatment'),
            ('holistic', 'Holistic/Alternative Approaches'),
            ('religious', 'Faith-Based Recovery'),
            ('self_help', 'Self-Help/Books'),
        ],
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="What approaches work for you?"
    )

    class Meta:
        model = UserProfile
        fields = [
            'bio', 'avatar', 'phone', 'emergency_contact', 'emergency_phone',
            'is_public', 'show_sobriety_date', 'allow_messages',
            'recovery_stage', 'addiction_type', 'interests', 'recovery_approach'
        ]
        widgets = {
            'bio': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Tell the community about your recovery journey...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            TabHolder(
                Tab(
                    'Basic Profile',
                    'avatar',
                    'bio',
                    'interests',
                ),
                Tab(
                    'Recovery Info',
                    'recovery_stage',
                    'addiction_type',
                    'recovery_approach',
                ),
                Tab(
                    'Contact & Privacy',
                    'phone',
                    'emergency_contact',
                    'emergency_phone',
                    Fieldset(
                        'Privacy Settings',
                        'is_public',
                        'show_sobriety_date',
                        'allow_messages',
                    ),
                ),
            ),
            Submit('submit', 'Update Profile', css_class='btn btn-primary')
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

    recovery_stage = forms.ChoiceField(
        choices=[
            ('', 'Any Recovery Stage'),
            ('early', 'Early Recovery'),
            ('sustained', 'Sustained Recovery'),
            ('stable', 'Stable Recovery'),
            ('long-term', 'Long-term Recovery'),
            ('supporter', 'Supporters'),
        ],
        required=False
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

    has_buddy = forms.BooleanField(
        required=False,
        label='Available for buddy partnership'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.layout = Layout(
            Div(
                Div('search', css_class='col-md-6'),
                Div('recovery_stage', css_class='col-md-6'),
                css_class='row'
            ),
            Div(
                Div('location', css_class='col-md-4'),
                Div('is_sponsor', css_class='col-md-4'),
                Div('has_buddy', css_class='col-md-4'),
                css_class='row'
            ),
            Submit('submit', 'Search', css_class='btn btn-outline-primary')
        )

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
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'daily_goal_description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'rules_and_guidelines': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'completion_message': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'challenge_type': forms.Select(attrs={'class': 'form-control'}),
            'duration_days': forms.Select(attrs={'class': 'form-control'}),
            'max_participants': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'completion_badge_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'title': 'Give your challenge a motivating name (e.g., "30 Days of Gratitude")',
            'description': 'Explain what this challenge is about and why people should join',
            'daily_goal_description': 'What do participants need to do each day? Be specific.',
            'rules_and_guidelines': 'Optional: Any special rules or guidelines for this challenge',
            'max_participants': 'Leave blank for unlimited participants',
            'completion_badge_name': 'Custom badge name (e.g., "Gratitude Champion")',
            'completion_message': 'Congratulatory message shown when someone completes the challenge',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Add CSS classes for styling
        for field_name, field in self.fields.items():
            if field_name not in ['is_public', 'allow_buddy_system', 'enable_leaderboard', 'enable_daily_check_in']:
                field.widget.attrs.update({'class': 'form-control'})
            else:
                field.widget.attrs.update({'class': 'form-check-input'})

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')

        if start_date and start_date < timezone.now().date():
            raise forms.ValidationError("Start date cannot be in the past")

        return cleaned_data


class JoinChallengeForm(forms.ModelForm):
    """Form for joining a challenge"""

    class Meta:
        model = ChallengeParticipant
        fields = ['personal_goal', 'motivation_note']
        widgets = {
            'personal_goal': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'What do you hope to achieve in this challenge?'
            }),
            'motivation_note': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'What motivates you to take on this challenge?'
            }),
        }
        help_texts = {
            'personal_goal': 'Set a personal goal for this challenge (optional)',
            'motivation_note': 'Share what motivates you to participate (optional)',
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
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'How did today go? Any challenges or wins to share?'
            }),
            'mood': forms.Select(attrs={'class': 'form-control'}),
            'custom_metric_1': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': 'e.g., minutes exercised, pages read'
            }),
            'custom_metric_2': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': 'additional metric'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.challenge = kwargs.pop('challenge', None)
        super().__init__(*args, **kwargs)

        # Customize labels based on challenge type
        if self.challenge:
            if self.challenge.challenge_type == 'exercise':
                self.fields['custom_metric_1'].label = 'Minutes Exercised'
                self.fields['custom_metric_2'].label = 'Steps (optional)'
            elif self.challenge.challenge_type == 'mindfulness':
                self.fields['custom_metric_1'].label = 'Minutes Meditated'
                self.fields['custom_metric_2'].label = 'Mindfulness Sessions'
            elif self.challenge.challenge_type == 'learning':
                self.fields['custom_metric_1'].label = 'Study Time (minutes)'
                self.fields['custom_metric_2'].label = 'Pages/Chapters'
            else:
                self.fields['custom_metric_1'].label = 'Metric 1 (optional)'
                self.fields['custom_metric_2'].label = 'Metric 2 (optional)'


class ChallengeCommentForm(forms.ModelForm):
    """Form for commenting on challenge check-ins"""

    class Meta:
        model = ChallengeComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': 'Share some encouragement or support...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].label = ''


class BuddyRequestForm(forms.Form):
    """Form for requesting an accountability partner"""

    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Why would you like this person as your accountability partner?'
        }),
        required=False,
        help_text='Optional message to send with your buddy request'
    )


class ChallengeFilterForm(forms.Form):
    """Form for filtering challenges"""

    FILTER_CHOICES = [
        ('', 'All Challenges'),
        ('active', 'Active'),
        ('upcoming', 'Upcoming'),
        ('completed', 'Completed'),
    ]

    TYPE_CHOICES = [('', 'All Types')] + list(GroupChallenge.CHALLENGE_TYPES)

    DURATION_CHOICES = [('', 'Any Duration')] + \
        list(GroupChallenge.DURATION_CHOICES)

    status = forms.ChoiceField(
        choices=FILTER_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    challenge_type = forms.ChoiceField(
        choices=TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    duration = forms.ChoiceField(
        choices=DURATION_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search challenges...'
        })
    )

    my_challenges_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
