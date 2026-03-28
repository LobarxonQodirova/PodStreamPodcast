from django.contrib.auth import get_user_model
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserSerializer,
    UserProfileUpdateSerializer,
    ChangePasswordSerializer,
    PublicPodcasterSerializer,
)
from .permissions import IsAdmin

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login endpoint returning JWT tokens with user data."""

    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    """User registration endpoint."""

    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get or update the current user's profile."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UserProfileUpdateSerializer
        return UserSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """Change password for authenticated user."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response(
            {"detail": "Password updated successfully."},
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """Blacklist the refresh token on logout."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"detail": "Invalid token."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PodcasterListView(generics.ListAPIView):
    """List all public podcaster profiles."""

    serializer_class = PublicPodcasterSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return User.objects.filter(
            role__in=[User.Role.PODCASTER, User.Role.ADMIN],
            is_active=True,
        ).order_by("-podcaster_since")


class PodcasterDetailView(generics.RetrieveAPIView):
    """Retrieve a public podcaster profile."""

    serializer_class = PublicPodcasterSerializer
    permission_classes = [permissions.AllowAny]
    queryset = User.objects.filter(
        role__in=[User.Role.PODCASTER, User.Role.ADMIN],
        is_active=True,
    )
    lookup_field = "id"


class UpgradeToPodcasterView(APIView):
    """Upgrade a listener account to podcaster."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role == User.Role.PODCASTER:
            return Response(
                {"detail": "Already a podcaster."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user.role == User.Role.ADMIN:
            return Response(
                {"detail": "Admin accounts cannot be downgraded."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.role = User.Role.PODCASTER
        from django.utils import timezone
        user.podcaster_since = timezone.now()
        user.save(update_fields=["role", "podcaster_since"])
        return Response(
            {"detail": "Account upgraded to podcaster.", "user": UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )


@api_view(["GET"])
@permission_classes([IsAdmin])
def admin_user_list(request):
    """Admin endpoint to list all users with filters."""
    queryset = User.objects.all()

    role = request.query_params.get("role")
    if role:
        queryset = queryset.filter(role=role)

    search = request.query_params.get("search")
    if search:
        queryset = queryset.filter(
            models.Q(email__icontains=search) |
            models.Q(display_name__icontains=search)
        )

    from rest_framework.pagination import PageNumberPagination
    paginator = PageNumberPagination()
    paginator.page_size = 50
    page = paginator.paginate_queryset(queryset, request)
    serializer = UserSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)
