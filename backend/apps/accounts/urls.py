from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = "accounts"

urlpatterns = [
    # Authentication
    path("login/", views.CustomTokenObtainPairView.as_view(), name="login"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),

    # Profile
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("change-password/", views.ChangePasswordView.as_view(), name="change-password"),
    path("upgrade-podcaster/", views.UpgradeToPodcasterView.as_view(), name="upgrade-podcaster"),

    # Public podcaster profiles
    path("podcasters/", views.PodcasterListView.as_view(), name="podcaster-list"),
    path("podcasters/<uuid:id>/", views.PodcasterDetailView.as_view(), name="podcaster-detail"),

    # Admin
    path("admin/users/", views.admin_user_list, name="admin-user-list"),
]
