import logging
from typing import TYPE_CHECKING, Type

from django.http import JsonResponse
from rest_framework import status
from rest_framework.views import APIView

from conf.authentication import HawkOnlyAuthentication
from mail import icms_serializers
from mail.enums import LicenceTypeEnum
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

        serializer_cls = self.get_serializer_cls(data["type"])
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

        logger.info("Created LicencePayload [%s, %s, %s]", licence.lite_id, licence.reference, licence.action)

        return JsonResponse(
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            data={"licence": licence.data},
        )

    def get_serializer_cls(self, app_type: str) -> Type["Serializer"]:
        serializers = {
            LicenceTypeEnum.IMPORT_OIL: icms_serializers.FirearmOilLicenceDataSerializer,
            LicenceTypeEnum.IMPORT_DFL: icms_serializers.FirearmDflLicenceDataSerializer,
            LicenceTypeEnum.IMPORT_SIL: icms_serializers.FirearmSilLicenceDataSerializer,
            LicenceTypeEnum.IMPORT_SAN: icms_serializers.SanctionLicenceDataSerializer,
        }

        return serializers[app_type]
