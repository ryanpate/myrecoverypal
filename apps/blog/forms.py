from django import forms
from ckeditor.widgets import CKEditorWidget
from .models import Post, Comment, Category, Tag
from django.utils.text import slugify

class PostForm(forms.ModelForm):
    """Form for creating and editing blog posts with rich text editor"""

    content = forms.CharField(
        widget=CKEditorWidget(config_name='default'),
        help_text='You can paste content directly from Medium or other sources'
    )

    # Add a field for new tags (comma-separated)
    new_tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter tags separated by commas (e.g., recovery, wellness, mindfulness)'
        }),
        help_text='Add tags separated by commas'
    )

    class Meta:
        model = Post
        fields = ['title', 'excerpt', 'content', 'category', 'tags',
                  'featured_image', 'is_personal_story', 'trigger_warning',
                  'trigger_description', 'status', 'meta_description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your post title'
            }),
            'excerpt': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Brief description of your post (optional)'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'tags': forms.SelectMultiple(attrs={
                'class': 'form-control'
            }),
            'trigger_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description of potential triggers'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'meta_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SEO description (max 160 characters)'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make some fields optional
        self.fields['excerpt'].required = False
        self.fields['featured_image'].required = False
        self.fields['tags'].required = False

        # Customize labels
        self.fields['is_personal_story'].label = 'This is my personal recovery story'
        self.fields['trigger_warning'].label = 'This content may contain triggers'

        # Only show trigger description if trigger warning is checked
        self.fields['trigger_description'].widget.attrs['style'] = 'display:none;'

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Auto-generate slug if not provided
        if not instance.slug:
            base_slug = slugify(instance.title)
            slug = base_slug
            counter = 1
            while Post.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = slug

        if commit:
            instance.save()

            # Handle new tags
            if self.cleaned_data.get('new_tags'):
                tag_names = [tag.strip()
                             for tag in self.cleaned_data['new_tags'].split(',')]
                for tag_name in tag_names:
                    if tag_name:
                        tag, created = Tag.objects.get_or_create(
                            name=tag_name,
                            defaults={'slug': slugify(tag_name)}
                        )
                        instance.tags.add(tag)

            # Save the many-to-many relationships
            self.save_m2m()

        return instance


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Share your thoughts...'
            })
        }
