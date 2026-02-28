"""
Django-Q2 task wrappers for audit execution.

Provides helpers to enqueue one-off audit runs and manage recurring
schedules via django-q2.
"""

import logging

from django_q.models import Schedule
from django_q.tasks import async_task

logger = logging.getLogger(__name__)


def enqueue_audit(device_id, trigger="manual"):
    """
    Enqueue an asynchronous audit run for a device.

    Parameters
    ----------
    device_id : int
        Primary key of the device to audit.
    trigger : str
        Label for what triggered the run (``"manual"``, ``"api"``, etc.).
    """
    async_task(
        "audits.services.run_audit",
        device_id,
        trigger,
    )


def create_schedule(audit_schedule):
    """
    Create a django-q2 :class:`Schedule` for a recurring audit.

    The created schedule's ID is stored back on the ``audit_schedule``
    instance so it can be managed later.

    Parameters
    ----------
    audit_schedule : AuditSchedule
        The application-level schedule model instance.  Expected to have
        ``device_id``, ``cron_expression``, and ``name`` attributes.
    """
    schedule = Schedule.objects.create(
        func="audits.services.run_audit",
        args=str(audit_schedule.device_id),
        kwargs="trigger='scheduled'",
        schedule_type=Schedule.CRON,
        cron=audit_schedule.cron_expression,
        name=f"netaudit-{audit_schedule.name}",
        repeats=-1,
    )
    audit_schedule.django_q_schedule_id = schedule.id
    audit_schedule.save(update_fields=["django_q_schedule_id"])
    logger.info(
        "Created django-q schedule %s for device %s",
        schedule.id,
        audit_schedule.device_id,
    )


def delete_schedule(audit_schedule):
    """
    Remove the django-q2 :class:`Schedule` associated with an audit schedule.

    Parameters
    ----------
    audit_schedule : AuditSchedule
        The application-level schedule model instance.  If
        ``django_q_schedule_id`` is not set, this is a no-op.
    """
    if not audit_schedule.django_q_schedule_id:
        return

    try:
        Schedule.objects.filter(
            pk=audit_schedule.django_q_schedule_id
        ).delete()
        logger.info(
            "Deleted django-q schedule %s",
            audit_schedule.django_q_schedule_id,
        )
    except Exception:
        logger.exception(
            "Failed to delete django-q schedule %s",
            audit_schedule.django_q_schedule_id,
        )

    audit_schedule.django_q_schedule_id = None
    audit_schedule.save(update_fields=["django_q_schedule_id"])
