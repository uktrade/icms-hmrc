from django.urls import path

from mail.views import SendMailView, ReadMailView, SeedMail

app_name = "mail"

urlpatterns = [
    path("send", SendMailView.as_view(), name="send_mail"),
    path("read", ReadMailView.as_view(), name="read_mail"),
    path("seed", SeedMail.as_view(), name="seed"),
]
