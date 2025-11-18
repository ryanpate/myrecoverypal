# Generated manually
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_rename_invoices_user_invoice_idx_invoices_user_id_e82a6a_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name='socialpostcomment',
            name='parent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='replies',
                to='accounts.socialpostcomment'
            ),
        ),
        migrations.AddField(
            model_name='socialpostcomment',
            name='likes',
            field=models.ManyToManyField(
                blank=True,
                related_name='liked_comments',
                to=settings.AUTH_USER_MODEL
            ),
        ),
    ]
