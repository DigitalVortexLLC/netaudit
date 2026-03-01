from allauth.account.adapter import DefaultAccountAdapter

from .models import User


class AccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        # First user ever gets admin role
        if not User.objects.exists():
            user.role = User.Role.ADMIN
        if commit:
            user.save()
        return user
