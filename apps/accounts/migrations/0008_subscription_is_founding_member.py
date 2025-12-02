# Generated manually for founding member feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_add_comment_likes_and_threading'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='is_founding_member',
            field=models.BooleanField(default=False, help_text='Early adopter with lifetime premium access'),
        ),
    ]
