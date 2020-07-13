from django.urls import path

from mail.views import UpdateLicence, ManageInbox

app_name = "mail"

urlpatterns = [
    path("update-licence/", UpdateLicence.as_view(), name="update_licence"),
    path("manage-inbox/", ManageInbox.as_view(), name="manage_inbox"),
]
