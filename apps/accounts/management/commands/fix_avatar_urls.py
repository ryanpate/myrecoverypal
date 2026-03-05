import re
from django.core.management.base import BaseCommand
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Fix avatar fields that contain full Cloudinary URLs instead of relative paths'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be fixed without saving')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        fixed = 0

        for user in User.objects.exclude(avatar='').exclude(avatar__isnull=True):
            val = str(user.avatar)

            if 'cloudinary.com' not in val and 'http' not in val:
                continue

            # Extract the relative path from the full URL
            # e.g. "https://res.cloudinary.com/xxx/image/upload/v123/avatars/abc.jpg"
            #   -> "avatars/abc.jpg"
            match = re.search(r'avatars/[^/]+\.\w+$', val)
            if match:
                new_val = match.group(0)
                self.stdout.write(
                    f'{"[DRY RUN] " if dry_run else ""}Fixing {user.username} (id={user.id}): '
                    f'{val} -> {new_val}'
                )
                if not dry_run:
                    user.avatar = new_val
                    user.save(update_fields=['avatar'])
                fixed += 1
            else:
                self.stdout.write(self.style.WARNING(
                    f'Could not parse avatar URL for {user.username} (id={user.id}): {val}'
                ))

        if fixed:
            self.stdout.write(self.style.SUCCESS(f'Fixed {fixed} avatar(s){"  (dry run)" if dry_run else ""}'))
        else:
            self.stdout.write('No broken avatar URLs found.')
