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

        # TODO: Rename this key now we have removed the UUID primary key field
        lite_id = data.pop("id")

        # TODO: get_or_create should be replaced now we have removed the lite code
        licence, created = LicencePayload.objects.get_or_create(
            lite_id=lite_id,
            reference=data["reference"],
            action=data["action"],
            skip_process=False,
            defaults=dict(
                lite_id=lite_id,
                reference=data["reference"],
                data=data,
            ),
        )

        logger.info(
            "Created LicencePayload [%s, %s, %s]",
            licence.lite_id,
            licence.reference,
            licence.action,
        )

        return JsonResponse(
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            data={"licence": licence.data},
        )


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
