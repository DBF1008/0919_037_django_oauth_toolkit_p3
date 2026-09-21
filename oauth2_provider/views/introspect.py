import calendar

from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from ..compat import login_not_required
from ..models import get_access_token_model, hash_token
from ..settings import oauth2_settings
from ..views.generic import ClientProtectedScopedResourceView


INTROSPECT_CACHE_KEY_PREFIX = "oauth2_provider:introspect"


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(login_not_required, name="dispatch")
class IntrospectTokenView(ClientProtectedScopedResourceView):
    """
    Implements an endpoint for token introspection based
    on RFC 7662 https://rfc-editor.org/rfc/rfc7662.html

    To access this view the request must pass a OAuth2 Bearer Token
    which is allowed to access the scope `introspection`.
    """

    required_scopes = ["introspection"]

    @staticmethod
    def get_token_response(token_value=None):
        if token_value is None:
            return JsonResponse(
                {"error": "invalid_request", "error_description": "Token parameter is missing."},
                status=400,
            )

        cache_timeout = oauth2_settings.INTROSPECT_TOKEN_CACHING_SECONDS
        cache_key = None
        if cache_timeout > 0:
            cache_key = f"{INTROSPECT_CACHE_KEY_PREFIX}:{hash_token(token_value)}"
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return JsonResponse(cached_data, status=200)

        token = get_access_token_model().objects.get_by_token(token_value)
        if token is not None and token.is_valid():
            data = {
                "active": True,
                "scope": token.scope,
                "exp": int(calendar.timegm(token.expires.timetuple())),
            }
            if token.application:
                data["client_id"] = token.application.client_id
            if token.user:
                data["username"] = token.user.get_username()
        else:
            data = {"active": False}

        if cache_key is not None:
            timeout = cache_timeout
            if token is not None and token.expires is not None:
                # Never serve a cached response past the token's own expiry.
                timeout = min(timeout, max(0, (token.expires - timezone.now()).total_seconds()))
            if timeout > 0:
                cache.set(cache_key, data, timeout)

        return JsonResponse(data, status=200)

    def get(self, request, *args, **kwargs):
        """
        Get the token from the URL parameters.
        URL: https://example.com/introspect?token=mF_9.B5f-4.1JqM

        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        return self.get_token_response(request.GET.get("token", None))

    def post(self, request, *args, **kwargs):
        """
        Get the token from the body form parameters.
        Body: token=mF_9.B5f-4.1JqM

        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        return self.get_token_response(request.POST.get("token", None))
