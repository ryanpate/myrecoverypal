# Generated manually
# NOTE: fields (parent, likes) were already added in 0006. This migration is a
# no-op kept only to preserve the dependency chain for subsequent migrations.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_rename_invoices_user_invoice_idx_invoices_user_id_e82a6a_idx_and_more"),
    ]

    operations = []
