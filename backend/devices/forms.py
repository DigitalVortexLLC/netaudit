from django import forms
from django.forms import inlineformset_factory

from .models import Device, DeviceGroup, DeviceHeader


class DeviceGroupForm(forms.ModelForm):
    devices = forms.ModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = DeviceGroup
        fields = ["name", "description", "devices"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["devices"].initial = self.instance.devices.all()

    def save(self, commit=True):
        group = super().save(commit=commit)
        if commit:
            group.devices.set(self.cleaned_data["devices"])
        return group


class DeviceForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=DeviceGroup.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Device
        fields = ["name", "hostname", "api_endpoint", "enabled", "groups"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["groups"].initial = self.instance.groups.all()
        self.fields["api_endpoint"].required = False
        self.fields["api_endpoint"].help_text = (
            "Leave blank to use the default endpoint."
        )

    def save(self, commit=True):
        device = super().save(commit=commit)
        if commit:
            device.groups.set(self.cleaned_data["groups"])
        return device


DeviceHeaderFormSet = inlineformset_factory(
    Device,
    DeviceHeader,
    fields=["key", "value"],
    extra=1,
    can_delete=True,
)
