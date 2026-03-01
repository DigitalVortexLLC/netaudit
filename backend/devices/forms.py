from django import forms
from django.forms import inlineformset_factory

from .models import Device, DeviceHeader


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ["name", "hostname", "api_endpoint", "enabled"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["api_endpoint"].required = False
        self.fields["api_endpoint"].help_text = (
            "Leave blank to use the default endpoint."
        )


DeviceHeaderFormSet = inlineformset_factory(
    Device,
    DeviceHeader,
    fields=["key", "value"],
    extra=1,
    can_delete=True,
)
