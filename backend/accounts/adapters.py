from allauth.account.adapter import DefaultAccountAdapter

from .models import User


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        from settings.models import SiteSettings

        return SiteSettings.load().public_registration_enabled

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        # First user ever gets admin role
        if not User.objects.exists():
            user.role = User.Role.ADMIN
        if commit:
            user.save()
        return user
