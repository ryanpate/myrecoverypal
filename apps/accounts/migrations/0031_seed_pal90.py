from django.db import migrations


def seed_pal90(apps, schema_editor):
    Promo = apps.get_model('accounts', 'Promo')
    Promo.objects.update_or_create(
        code='PAL90',
        defaults={
            'trial_days': 60,
            'description': '90 Day Recovery Journal back cover',
            'active': True,
        },
    )


def remove_pal90(apps, schema_editor):
    Promo = apps.get_model('accounts', 'Promo')
    Promo.objects.filter(code='PAL90').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0030_promo_models'),
    ]
    operations = [
        migrations.RunPython(seed_pal90, remove_pal90),
    ]
