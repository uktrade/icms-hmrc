from django.urls import path

from mail import views

app_name = "mail"

urlpatterns = [
    path("update-licence/", views.LicenceDataIngestView.as_view(), name="update_licence"),
    path("licence/", views.Licence.as_view(), name="licence"),
]
