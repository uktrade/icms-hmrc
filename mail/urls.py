from django.urls import path

from mail import views

app_name = "mail"

urlpatterns = [
    path("update-licence/", views.LicenceDataIngestView.as_view(), name="update_licence"),
    path(
        "check-icms-hmrc-connection/",
        views.CheckICMSHMRCConnectionView.as_view(),
        name="check_icms_hmrc_connection",
    ),
]
