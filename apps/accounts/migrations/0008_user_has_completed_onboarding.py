# Generated manually for onboarding feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_add_comment_likes_and_threading'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='has_completed_onboarding',
            field=models.BooleanField(default=False, help_text='Has the user completed the onboarding wizard?'),
        ),
    ]
