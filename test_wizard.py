import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from organizations.models import Organization
from api.services.setup_progress import SetupProgressService

org = Organization.objects.first()
progress = SetupProgressService.get_progress(org)
print('Percentage:', progress['percentage'])
print('Is Complete:', progress['is_complete'])
print('Steps:')
for step in progress['steps']:
    print(f"- {step['title']}: {step['is_completed']}")
