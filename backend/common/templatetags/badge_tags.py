from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter
def badge(value):
    """Render a status/outcome badge."""
    label = str(value).replace("_", " ").title()
    css_class = str(value).lower()
    return format_html('<span class="badge badge-{}">{}</span>', css_class, label)


@register.filter
def severity_badge(value):
    """Render a severity badge."""
    label = str(value).title()
    css_class = str(value).lower()
    return format_html('<span class="badge badge-{}">{}</span>', css_class, label)


@register.filter
def enabled_badge(value):
    """Render an enabled/disabled badge."""
    if value:
        return format_html('<span class="badge badge-enabled">Enabled</span>')
    return format_html('<span class="badge badge-disabled">Disabled</span>')
