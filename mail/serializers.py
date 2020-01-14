from rest_framework import serializers

from mail.models import Mail, LicenceUpdate


class LicenceUpdateSerializer(serializers.ModelSerializer):
    mail = serializers.PrimaryKeyRelatedField(
        queryset=Mail.objects.all(), required=False
    )

    class Meta:
        model = LicenceUpdate
        fields = "__all__"


class LicenceUpdateMailSerializer(serializers.ModelSerializer):
    licence_update = LicenceUpdateSerializer(write_only=True)

    class Meta:
        model = Mail
        fields = [
            "id",
            "created_at",
            "edi_filename",
            "edi_data",
            "extract_type",
            "raw_data",
            "licence_update",
        ]

    def create(self, validated_data):
        licence_update_data = validated_data.pop("licence_update")
        mail = Mail.objects.create(**validated_data)

        licence_update_data["mail"] = mail.id

        licence_update_serializer = LicenceUpdateSerializer(data=licence_update_data)
        if licence_update_serializer.is_valid():
            licence_update_serializer.save()
        else:
            raise serializers.ValidationError(licence_update_serializer.errors)

        return mail


class LicenceUpdateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mail
        fields = ["last_submitted_on", "status", "response_file", "response_data"]


class InvalidEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mail
        fields = "__all__"
