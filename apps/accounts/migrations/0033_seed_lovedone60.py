from django.db import migrations


def seed_lovedone60(apps, schema_editor):
    Promo = apps.get_model('accounts', 'Promo')
    Promo.objects.update_or_create(
        code='LOVEDONE60',
        defaults={
            'trial_days': 60,
            'description': "Loved One's Recovery Journal back cover",
            'active': True,
        },
    )


def remove_lovedone60(apps, schema_editor):
    Promo = apps.get_model('accounts', 'Promo')
    Promo.objects.filter(code='LOVEDONE60').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0032_seed_christian60'),
    ]
    operations = [
        migrations.RunPython(seed_lovedone60, remove_lovedone60),
    ]
