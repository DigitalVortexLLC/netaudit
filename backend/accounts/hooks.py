import logging

logger = logging.getLogger(__name__)


class AuditLogHook:
    """Logs authentication events."""

    def post_authenticate(self, request):
        if hasattr(request, "user") and request.user.is_authenticated:
            logger.info(
                "auth.access user=%s path=%s method=%s",
                request.user.username,
                request.path,
                request.method,
            )
