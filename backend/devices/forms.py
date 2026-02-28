from django import forms
from django.forms import inlineformset_factory

from .models import Device, DeviceHeader


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ["name", "hostname", "api_endpoint", "enabled"]


DeviceHeaderFormSet = inlineformset_factory(
    Device,
    DeviceHeader,
    fields=["key", "value"],
    extra=1,
    can_delete=True,
)
