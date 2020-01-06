from django.urls import path

from mail.views import SendMailView, ReadMailView

app_name = "mail"

urlpatterns = [
    path("send", SendMailView.as_view(), name="send_mail"),
    path("read", ReadMailView.as_view(), name="read_mail"),
]
