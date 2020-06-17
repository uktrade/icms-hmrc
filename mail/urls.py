from django.urls import path

from mail.views import UpdateLicence

app_name = "mail"

urlpatterns = [
    path("update-licence/", UpdateLicence.as_view(), name="update_licence"),
]
