from django.db import migrations


def seed_christian60(apps, schema_editor):
    Promo = apps.get_model('accounts', 'Promo')
    Promo.objects.update_or_create(
        code='CHRISTIAN60',
        defaults={
            'trial_days': 60,
            'description': 'Christian Recovery Journal back cover',
            'active': True,
        },
    )


def remove_christian60(apps, schema_editor):
    Promo = apps.get_model('accounts', 'Promo')
    Promo.objects.filter(code='CHRISTIAN60').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0031_seed_pal90'),
    ]
    operations = [
        migrations.RunPython(seed_christian60, remove_christian60),
    ]
