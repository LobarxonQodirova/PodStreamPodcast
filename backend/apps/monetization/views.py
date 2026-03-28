import logging

from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.shortcuts import get_object_or_404

from apps.podcasts.models import Podcast
from apps.accounts.permissions import IsPodcaster

from .models import SponsorDeal, Donation, PremiumContent
from .serializers import (
    SponsorDealSerializer,
    SponsorDealCreateSerializer,
    DonationSerializer,
    DonationCreateSerializer,
    PremiumContentSerializer,
    PremiumContentCreateSerializer,
)

logger = logging.getLogger(__name__)


class SponsorDealListCreateView(generics.ListCreateAPIView):
    """List and create sponsor deals for a podcast."""

    permission_classes = [permissions.IsAuthenticated, IsPodcaster]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SponsorDealCreateSerializer
        return SponsorDealSerializer

    def get_queryset(self):
        qs = SponsorDeal.objects.filter(podcast__owner=self.request.user)
        podcast_id = self.request.query_params.get("podcast_id")
        if podcast_id:
            qs = qs.filter(podcast_id=podcast_id)
        return qs.select_related("podcast")


class SponsorDealDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Manage a specific sponsor deal."""

    serializer_class = SponsorDealSerializer
    permission_classes = [permissions.IsAuthenticated, IsPodcaster]

    def get_queryset(self):
        return SponsorDeal.objects.filter(podcast__owner=self.request.user)


class DonationListView(generics.ListAPIView):
    """List donations received by the podcaster."""

    serializer_class = DonationSerializer
    permission_classes = [permissions.IsAuthenticated, IsPodcaster]

    def get_queryset(self):
        qs = Donation.objects.filter(
            podcast__owner=self.request.user,
            status=Donation.Status.COMPLETED,
        )
        podcast_id = self.request.query_params.get("podcast_id")
        if podcast_id:
            qs = qs.filter(podcast_id=podcast_id)
        return qs.select_related("podcast", "donor")


class CreateDonationView(APIView):
    """Create a donation (tip) via Stripe."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DonationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        podcast = serializer.validated_data["podcast"]

        # Create Stripe payment intent
        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY

            amount_cents = int(serializer.validated_data["amount"] * 100)
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=serializer.validated_data.get("currency", "usd"),
                metadata={
                    "podcast_id": str(podcast.id),
                    "donor_id": str(request.user.id),
                    "type": "donation",
                },
            )

            donation = serializer.save(
                donor=request.user,
                stripe_payment_id=intent.id,
                status=Donation.Status.PENDING,
            )

            return Response(
                {
                    "donation_id": str(donation.id),
                    "client_secret": intent.client_secret,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Stripe payment creation failed: {e}")
            return Response(
                {"detail": "Payment processing failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class StripeWebhookView(APIView):
    """Handle Stripe webhook events for donation confirmation."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET,
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if event["type"] == "payment_intent.succeeded":
            payment_intent = event["data"]["object"]
            try:
                donation = Donation.objects.get(
                    stripe_payment_id=payment_intent["id"]
                )
                donation.status = Donation.Status.COMPLETED
                donation.stripe_charge_id = payment_intent.get("latest_charge", "")
                donation.save(update_fields=["status", "stripe_charge_id"])
                logger.info(f"Donation {donation.id} completed successfully.")
            except Donation.DoesNotExist:
                logger.warning(f"No donation found for payment {payment_intent['id']}")

        elif event["type"] == "payment_intent.payment_failed":
            payment_intent = event["data"]["object"]
            Donation.objects.filter(
                stripe_payment_id=payment_intent["id"]
            ).update(status=Donation.Status.FAILED)

        return Response({"status": "ok"})


class PremiumContentListCreateView(generics.ListCreateAPIView):
    """List and create premium content."""

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PremiumContentCreateSerializer
        return PremiumContentSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsPodcaster()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = PremiumContent.objects.select_related("podcast", "episode")
        podcast_id = self.request.query_params.get("podcast_id")
        if podcast_id:
            qs = qs.filter(podcast_id=podcast_id)
        if not self.request.user.is_authenticated:
            qs = qs.filter(is_published=True)
        return qs


class PremiumContentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Manage premium content."""

    serializer_class = PremiumContentSerializer
    permission_classes = [permissions.IsAuthenticated, IsPodcaster]

    def get_queryset(self):
        return PremiumContent.objects.filter(podcast__owner=self.request.user)
