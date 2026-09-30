"""Django 5.1 removed STATICFILES_STORAGE / DEFAULT_FILE_STORAGE: if settings
still use them, Django silently falls back to plain local storage (no hashed
static filenames, uploads written to the container's disk instead of
Cloudinary). These tests pin the STORAGES configuration."""
import os
import subprocess
import sys

from django.conf import settings
from django.core.files.storage import storages
from django.test import SimpleTestCase


class StorageSettingsTests(SimpleTestCase):
    def test_static_files_use_whitenoise_manifest_storage(self):
        from whitenoise.storage import CompressedManifestStaticFilesStorage
        self.assertIsInstance(
            storages['staticfiles'], CompressedManifestStaticFilesStorage)

    def test_media_uses_cloudinary_when_configured(self):
        env = dict(os.environ, CLOUDINARY_CLOUD_NAME='demo',
                   CLOUDINARY_API_KEY='k', CLOUDINARY_API_SECRET='s',
                   DJANGO_SETTINGS_MODULE='recovery_hub.settings')
        out = subprocess.run(
            [sys.executable, '-c',
             'import django; django.setup();'
             'from django.core.files.storage import storages;'
             'print("default=" + type(storages["default"]).__name__)'],
            cwd=settings.BASE_DIR, env=env, capture_output=True, text=True)
        self.assertIn('default=MediaCloudinaryStorage', out.stdout, out.stderr[-500:])
