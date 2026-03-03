"""WebSocket JWT authentication middleware for Django Channels."""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def get_user_from_token(token_str):
    """Validate a JWT access token and return the corresponding user."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        token = AccessToken(token_str)
        return User.objects.get(pk=token["user_id"])
    except Exception:
        return AnonymousUser()


class JWTWebSocketMiddleware(BaseMiddleware):
    """Extract JWT from query string ``?token=...`` and set ``scope["user"]``."""

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token_list = params.get("token", [])

        if token_list:
            scope["user"] = await get_user_from_token(token_list[0])
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
