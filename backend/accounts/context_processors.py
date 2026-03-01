def user_role(request):
    """Expose user role to all templates."""
    if hasattr(request, "user") and request.user.is_authenticated:
        return {"user_role": request.user.role}
    return {"user_role": None}
