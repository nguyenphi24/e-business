from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.identity.models import User
from apps.identity.serializers import UserMeSerializer
from common.exceptions import DomainError


def _cookie_options():
    return {
        "httponly": True,
        "secure": settings.REFRESH_COOKIE_SECURE,
        "samesite": settings.REFRESH_COOKIE_SAMESITE,
        "max_age": int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        "path": "/api/v1/auth/",
    }


def _set_refresh_cookie(response, token):
    response.set_cookie(settings.REFRESH_COOKIE_NAME, str(token), **_cookie_options())


def _check_origin(request):
    origin = request.headers.get("Origin")
    if origin and origin not in settings.CORS_ALLOWED_ORIGINS:
        raise DomainError("permission_denied", "Request origin is not allowed.", status_code=403)


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return refresh, str(refresh.access_token)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        if not email or not password:
            raise DomainError(
                "validation_error",
                "Email and password are required.",
                status_code=422,
                field_errors={"email": ["This field is required."], "password": ["This field is required."]},
            )

        user = authenticate(request=request, username=email, password=password)
        if not user or not user.is_active:
            raise DomainError("invalid_credentials", "Invalid email or password.", status_code=401)

        refresh, access = _tokens_for_user(user)
        response = Response({"access": access, "user": UserMeSerializer(user).data})
        _set_refresh_cookie(response, refresh)
        return response


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        _check_origin(request)
        raw_token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not raw_token:
            raise DomainError("authentication_required", "Refresh cookie is missing.", status_code=401)

        try:
            old_refresh = RefreshToken(raw_token)
            old_refresh.check_blacklist()
            user = User.objects.get(pk=old_refresh["user_id"])
        except (TokenError, KeyError, ValueError, User.DoesNotExist):
            raise DomainError("invalid_refresh_token", "Refresh token is invalid or expired.", status_code=401)

        if not user.is_active:
            raise DomainError("invalid_refresh_token", "Refresh token is invalid or expired.", status_code=401)

        old_refresh.blacklist()
        refresh, access = _tokens_for_user(user)
        response = Response({"access": access, "user": UserMeSerializer(user).data})
        _set_refresh_cookie(response, refresh)
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        _check_origin(request)
        raw_token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if raw_token:
            try:
                RefreshToken(raw_token).blacklist()
            except TokenError:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(settings.REFRESH_COOKIE_NAME, path="/api/v1/auth/")
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserMeSerializer(request.user).data)
