import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recovery_hub.settings.development')

app = Celery('recovery_hub')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')