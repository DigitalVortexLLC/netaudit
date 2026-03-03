"""Django-Q2 task wrappers for config source operations."""
import logging

from django_q.tasks import async_task

logger = logging.getLogger(__name__)


def enqueue_fetch_config(device_id):
    async_task("config_sources.tasks.run_fetch_config", device_id)


def run_fetch_config(device_id):
    from devices.models import Device

    from .fetchers import fetch_config

    device = Device.objects.get(pk=device_id)
    fetch_config(device)
    logger.info("Config fetched for device %s (id=%d)", device.name, device.id)
