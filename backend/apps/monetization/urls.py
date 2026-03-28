from django.urls import path
from . import views

app_name = "monetization"

urlpatterns = [
    # Sponsor Deals
    path("sponsors/", views.SponsorDealListCreateView.as_view(), name="sponsor-list-create"),
    path("sponsors/<uuid:pk>/", views.SponsorDealDetailView.as_view(), name="sponsor-detail"),

    # Donations / Tips
    path("donations/", views.DonationListView.as_view(), name="donation-list"),
    path("donate/", views.CreateDonationView.as_view(), name="create-donation"),
    path("stripe/webhook/", views.StripeWebhookView.as_view(), name="stripe-webhook"),

    # Premium Content
    path("premium/", views.PremiumContentListCreateView.as_view(), name="premium-list-create"),
    path("premium/<uuid:pk>/", views.PremiumContentDetailView.as_view(), name="premium-detail"),
]
