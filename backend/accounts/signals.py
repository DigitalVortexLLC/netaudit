from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def sync_role_to_group(sender, instance, **kwargs):
    """Keep the user's Django group in sync with their role field."""
    role_group_names = {choice[0] for choice in User.Role.choices}
    # Remove user from all role groups
    role_groups = Group.objects.filter(name__in=role_group_names)
    instance.groups.remove(*role_groups)
    # Add user to current role group
    group, _ = Group.objects.get_or_create(name=instance.role)
    instance.groups.add(group)
