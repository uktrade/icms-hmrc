from django.urls import path

from mail.views import UpdateLicence, ManageInbox, SendLicenceUpdatesToHmrc

app_name = "mail"

urlpatterns = [
    path("update-licence/", UpdateLicence.as_view(), name="update_licence"),
    path("manage-inbox/", ManageInbox.as_view(), name="manage_inbox"),
    path("send-licence-updates-to-hmrc/", SendLicenceUpdatesToHmrc.as_view(), name="send_updates_to_hmrc"),
]
