from django import template

register = template.Library()


@register.simple_tag
def active_class(request, path, exact=False):
    if exact:
        return "active" if request.path == path else ""
    return "active" if request.path.startswith(path) else ""
