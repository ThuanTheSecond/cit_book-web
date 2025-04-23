from celery import Celery
import os

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_cit_web.settings')

# Create Celery app
celery_app = Celery('book_cit_web')

# Load task modules from all registered Django app configs
celery_app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
celery_app.autodiscover_tasks()

# Optional: Configure Celery to handle errors
@celery_app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
