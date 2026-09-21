from celery import shared_task
from django.core.management import call_command


@shared_task(ignore_result=True)
def update_evropochta_branches():
    """Ежедневное обновление списка отделений Европочты."""
    call_command('fetch_evropochta')