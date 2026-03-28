from rest_framework.permissions import BasePermission


class IsPodcaster(BasePermission):
    """Allow access only to users with podcaster or admin role."""

    message = "You must be a podcaster to perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ("podcaster", "admin")
        )


class IsAdmin(BasePermission):
    """Allow access only to admin users."""

    message = "Admin access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )


class IsOwnerOrReadOnly(BasePermission):
    """Allow write access only to the object owner."""

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        # Check various owner field names
        if hasattr(obj, "owner"):
            return obj.owner == request.user
        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "author"):
            return obj.author == request.user
        return False


class IsPodcastOwner(BasePermission):
    """Allow access only to the podcast owner."""

    message = "You must be the podcast owner to perform this action."

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "podcast"):
            return obj.podcast.owner == request.user
        if hasattr(obj, "owner"):
            return obj.owner == request.user
        return False


class IsOwnerOrAdmin(BasePermission):
    """Allow access to owner or admin."""

    def has_object_permission(self, request, view, obj):
        if request.user.role == "admin":
            return True
        if hasattr(obj, "owner"):
            return obj.owner == request.user
        if hasattr(obj, "user"):
            return obj.user == request.user
        return False
