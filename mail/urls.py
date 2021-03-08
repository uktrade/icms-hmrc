from django.urls import path

from mail import views

app_name = "mail"

urlpatterns = [
    path("update-licence/", views.LicenceDataIngestView.as_view(), name="update_licence"),
    # The endpoints below are for testing purposes; they can be enabled to manually trigger and debug Background Tasks
    # path("manage-inbox/", ManageInbox.as_view(), name="manage_inbox"),
    # path("send-usage-updates-to-lite-api/", SendUsageUpdatesToLiteApi.as_view(), name="send_updates_to_lite_api"),
    # path("send-licence-updates-to-hmrc/", SendLicenceUpdatesToHmrc.as_view(), name="send_updates_to_hmrc"),
]
