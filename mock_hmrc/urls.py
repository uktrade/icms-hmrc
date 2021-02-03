from django.conf import settings
from django.urls import path

from mock_hmrc import views

app_name = "mock_hmrc"

urlpatterns = []

if settings.DEBUG:
    urlpatterns = [
        path("handle-replies/", views.HandleReplies.as_view(), name="handle_replies"),
    ]
