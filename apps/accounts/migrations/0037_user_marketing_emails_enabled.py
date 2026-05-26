from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0036_seed_court_subscription_plans'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='marketing_emails_enabled',
            field=models.BooleanField(
                default=True,
                help_text='Receive weekly shop and milestone celebration emails.',
            ),
        ),
    ]
