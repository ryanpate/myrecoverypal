from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0023_seed_subscription_plans'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='activityfeed',
            index=models.Index(
                fields=['user', '-created_at'],
                name='accounts_ac_user_id_a3ad7a_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='activityfeed',
            index=models.Index(
                fields=['-created_at'],
                name='accounts_ac_created_7184d8_idx',
            ),
        ),
    ]
