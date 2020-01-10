from rest_framework import serializers

from mail.models import LicenseUpdate, InvalidEmail


class LicenseUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LicenseUpdate
        fields = "__all__"


class InvalidEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvalidEmail
        fields = "__all__"
