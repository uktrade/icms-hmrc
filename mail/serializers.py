import json
import logging
from datetime import datetime

from rest_framework import serializers

from mail import enums
from mail.models import LicenceData, LicenceIdMapping, Mail, UsageData


class MailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mail
        fields = ["status"]


class LicenceDataSerializer(serializers.ModelSerializer):
    mail = serializers.PrimaryKeyRelatedField(queryset=Mail.objects.all(), required=False)

    class Meta:
        model = LicenceData
        fields = "__all__"

    def create(self, validated_data):
        instance, _ = LicenceData.objects.get_or_create(**validated_data)
        return instance


class LicenceDataMailSerializer(serializers.ModelSerializer):
    licence_data = LicenceDataSerializer(write_only=True)

    class Meta:
        model = Mail
        fields = [
            "id",
            "edi_filename",
            "edi_data",
            "extract_type",
            "raw_data",
            "licence_data",
        ]

    def create(self, validated_data):
        licence_data = validated_data.pop("licence_data")
        # Mail object should not exist for licence_data, so we can create it here safely

        dups = Mail.objects.filter(**validated_data)

        if dups and dups.first().response_data and "rejected" in dups.first().response_data:
            validated_data["retry"] = True
            mail = Mail.objects.create(**validated_data)
        else:
            mail, _ = Mail.objects.get_or_create(**validated_data)

        licence_data["mail"] = mail.id

        licence_data_serializer = LicenceDataSerializer(data=licence_data)
        if licence_data_serializer.is_valid():
            licence_data_serializer.save()
        else:
            logging.error(licence_data_serializer.errors)
            raise serializers.ValidationError(licence_data_serializer.errors)
        return mail


class UpdateResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mail
        fields = ["extract_type", "status", "response_filename", "response_data", "response_subject"]

        def update(self, instance, validated_data):
            instance.status = validated_data["status"]
            instance.response_file = validated_data["response_filename"]
            instance.response_data = validated_data["response_data"]
            instance.response_subject = validated_data["response_subject"]

            instance.save()

            return instance


class UsageDataSerializer(serializers.ModelSerializer):
    mail = serializers.PrimaryKeyRelatedField(queryset=Mail.objects.all(), required=False)

    class Meta:
        model = UsageData
        fields = ("licence_ids", "mail", "spire_run_number", "hmrc_run_number")

    def create(self, validated_data):
        validated_data["licence_ids"] = json.loads(validated_data["licence_ids"])

        has_lite_data = False
        has_spire_data = False

        for licence in validated_data["licence_ids"]:
            if LicenceIdMapping.objects.filter(reference=licence).exists():
                has_lite_data = True
            else:
                has_spire_data = True

            validated_data["has_lite_data"] = has_lite_data
            validated_data["has_spire_data"] = has_spire_data

        instance, created = UsageData.objects.get_or_create(**validated_data)

        if created and instance.has_lite_data:
            instance.send_usage_updates_to_lite(instance.id)

        return instance


class UsageDataMailSerializer(serializers.ModelSerializer):
    usage_data = UsageDataSerializer(write_only=True)

    class Meta:
        model = Mail
        fields = [
            "id",
            "edi_filename",
            "edi_data",
            "extract_type",
            "raw_data",
            "usage_data",
        ]

    def create(self, validated_data):
        usage_data = validated_data.pop("usage_data")
        mail, created = Mail.objects.get_or_create(**validated_data)

        usage_data["mail"] = mail.id

        if created:
            serializer = UsageDataSerializer(data=usage_data)
            if serializer.is_valid():
                serializer.save()
            else:
                raise serializers.ValidationError(serializer.errors)

        return mail


class GoodSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField(max_length=2000, allow_blank=True)
    quantity = serializers.DecimalField(decimal_places=3, max_digits=13)
    unit = serializers.CharField()


class CountrySerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class AddressSerializer(serializers.Serializer):
    line_1 = serializers.CharField(allow_blank=False)
    line_2 = serializers.CharField(allow_blank=True, required=False)
    line_3 = serializers.CharField(allow_blank=True, required=False)
    line_4 = serializers.CharField(allow_blank=True, required=False)
    line_5 = serializers.CharField(allow_blank=True, required=False)
    postcode = serializers.CharField(allow_blank=True, required=False)
    country = CountrySerializer()


class TraderSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80, allow_blank=False)
    address = AddressSerializer()


class ForiegnTraderSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80, allow_blank=False)
    address = AddressSerializer()


class LiteLicenceDataSerializer(serializers.Serializer):
    id = serializers.CharField()
    reference = serializers.CharField(max_length=35)
    type = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    action = serializers.CharField()

    old_id = serializers.CharField(required=False)

    def validate(self, attrs):
        if self.initial_data.get("action") == enums.LicenceActionEnum.UPDATE and not attrs.get("old_id"):
            raise serializers.ValidationError("old_id is a required field for action - update")
        return attrs

    def validate_old_id(self, value):
        if (
            self.initial_data.get("action") == enums.LicenceActionEnum.UPDATE
            and not LicenceIdMapping.objects.filter(lite_id=value).exists()
        ):
            raise serializers.ValidationError("This licence does not exist in HMRC integration records")
        return value


class LicenceDataStatusSerializer(serializers.ModelSerializer):
    licence_data_status = serializers.SerializerMethodField()
    reply_pending_count = serializers.SerializerMethodField()
    processing_time = serializers.SerializerMethodField()

    class Meta:
        model = LicenceData
        fields = ("licence_data_status", "reply_pending_count", "processing_time")

    def get_licence_data_status(self, instance):
        if instance.mail.status == enums.ReceptionStatusEnum.PENDING:
            return f"The mail with run number {instance.hmrc_run_number} is not yet sent to HMRC (which is {instance.source_run_number} for {instance.source})"
        elif instance.mail.status == enums.ReceptionStatusEnum.REPLY_PENDING:
            return f"Reply pending, waiting for reply for HMRC run number {instance.hmrc_run_number} (which is {instance.source_run_number} for {instance.source})"  # noqa
        elif instance.mail.status == enums.ReceptionStatusEnum.REPLY_SENT:
            return f"Reply sent for run number {instance.hmrc_run_number} (which is {instance.source_run_number} for {instance.source}). Waiting for next mail from SPIRE/LITE"  # noqa

    def get_reply_pending_count(self, instance):
        return Mail.objects.filter(
            extract_type=enums.ExtractTypeEnum.LICENCE_DATA, status=enums.ReceptionStatusEnum.REPLY_PENDING
        ).count()

    def get_processing_time(self, instance):
        if instance.mail.status == enums.ReceptionStatusEnum.REPLY_PENDING:
            if instance.mail.sent_at:
                return int(datetime.now().timestamp() - instance.mail.sent_at.timestamp()) // 60
        elif instance.mail.status == enums.ReceptionStatusEnum.REPLY_SENT:
            if instance.mail.sent_at and instance.mail.response_date:
                return int((instance.mail.response_date - instance.mail.sent_at).total_seconds()) // 60

        return 0


class UsageDataStatusSerializer(serializers.ModelSerializer):
    usage_data_status = serializers.SerializerMethodField()

    class Meta:
        model = UsageData
        fields = ("usage_data_status", "has_lite_data")

    def get_usage_data_status(self, instance):
        return f"Run number of last usage data processed is {instance.hmrc_run_number}"
