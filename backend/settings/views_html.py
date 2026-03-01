from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import SiteSettingsForm
from .models import SiteSettings


def settings_view(request):
    site_settings = SiteSettings.load()
    if request.method == "POST":
        form = SiteSettingsForm(request.POST, instance=site_settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings saved.")
            return redirect("settings-html")
    else:
        form = SiteSettingsForm(instance=site_settings)
    return render(request, "settings/settings_form.html", {"form": form})
