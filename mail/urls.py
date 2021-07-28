from django.urls import path

from django.conf import settings

from mail import views

app_name = "mail"

urlpatterns = [path("update-licence/", views.LicenceDataIngestView.as_view(), name="update_licence")]

if settings.DEBUG:
    urlpatterns.extend(
        [
            path(
                "send-licence-updates-to-hmrc/", views.SendLicenceUpdatesToHmrc.as_view(), name="send_updates_to_hmrc"
            ),
            path("set-all-to-reply-sent/", views.SetAllToReplySent.as_view(), name="set_all_to_reply_sent"),
        ]
    )
