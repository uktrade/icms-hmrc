import logging
from typing import TYPE_CHECKING, Type

from django.http import JsonResponse
from rest_framework import status
from rest_framework.views import APIView

from conf.authentication import HawkOnlyAuthentication
from mail import serializers
from mail.enums import LicenceActionEnum, LicenceTypeEnum
from mail.models import LicencePayload

if TYPE_CHECKING:
    from rest_framework.serializers import Serializer  # noqa

logger = logging.getLogger(__name__)


class LicenceDataIngestView(APIView):
    authentication_classes = (HawkOnlyAuthentication,)

    def post(self, request):
        try:
            data = request.data["licence"]
        except KeyError:
            errors = [{"licence": "This field is required."}]
            logger.error(
                "Failed to create licence data for %s due to %s",
                request.data,
                errors,
            )
            return JsonResponse(status=status.HTTP_400_BAD_REQUEST, data={"errors": errors})

        serializer_cls = get_serializer_cls(data["type"], data["action"])
        serializer = serializer_cls(data=data)

        if not serializer.is_valid():
            errors = [{"licence": serializer.errors}]
            logger.error(
                "Failed to create licence data for %s due to %s",
                data,
                errors,
            )
            return JsonResponse(status=status.HTTP_400_BAD_REQUEST, data={"errors": errors})

        licence = LicencePayload.objects.create(
            action=data["action"],
            icms_id=data["id"],
            reference=data["reference"],
            data=data,
        )

        logger.info(
            "Created LicencePayload [%s, %s, %s]",
            licence.reference,
            licence.action,
            licence.icms_id,
        )

        return JsonResponse(status=status.HTTP_201_CREATED, data={"licence": licence.data})


def get_serializer_cls(app_type: str, action: str) -> Type["Serializer"]:
    if action == LicenceActionEnum.CANCEL:
        return serializers.RevokeLicenceDataSerializer

    # "insert" and "replace" serializer
    match app_type:
        case LicenceTypeEnum.IMPORT_OIL:
            return serializers.FirearmOilLicenceDataSerializer
        case LicenceTypeEnum.IMPORT_DFL:
            return serializers.FirearmDflLicenceDataSerializer
        case LicenceTypeEnum.IMPORT_SIL:
            return serializers.FirearmSilLicenceDataSerializer
        case LicenceTypeEnum.IMPORT_SAN:
            return serializers.SanctionLicenceDataSerializer
        case _:
            raise ValueError(f"Unsupported app type: ({app_type})")
