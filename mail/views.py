import logging

from django.http import JsonResponse, HttpResponse
from rest_framework import status
from rest_framework.views import APIView

from conf.authentication import HawkOnlyAuthentication
from mail.enums import LicenceTypeEnum, LicenceActionEnum
from mail.models import LicencePayload, LicenceIdMapping, UsageUpdate
from mail.serializers import (
    LiteLicenceUpdateSerializer,
    ForiegnTraderSerializer,
    GoodSerializer,
)
from mail.tasks import manage_inbox, send_licence_updates_to_hmrc, send_licence_usage_figures_to_lite_api
from rest_framework.status import HTTP_200_OK


class UpdateLicence(APIView):
    authentication_classes = (HawkOnlyAuthentication,)

    def post(self, request):
        errors = []

        licence = request.data.get("licence")

        if not licence:
            errors.append({"licence": "This field is required."})
        else:
            serializer = LiteLicenceUpdateSerializer(data=licence)
            if not serializer.is_valid():
                errors.append({"licence": serializer.errors})
            else:
                if licence.get("action") == LicenceActionEnum.UPDATE:
                    licence["old_reference"] = LicenceIdMapping.objects.get(lite_id=licence["old_id"]).reference
                else:
                    licence.pop("old_id", None)

            if licence.get("type") in LicenceTypeEnum.OPEN_LICENCES + LicenceTypeEnum.OPEN_GENERAL_LICENCES:
                countries = licence.get("countries")
                if not countries:
                    errors.append({"countries": "This field is required."})

            if licence.get("type") in LicenceTypeEnum.STANDARD_LICENCES:
                end_user = licence.get("end_user")
                if not end_user:
                    errors.append({"end_user": "This field is required."})
                else:
                    serializer = ForiegnTraderSerializer(data=end_user)
                    if not serializer.is_valid():
                        errors.append({"end_user": serializer.errors})

                goods = licence.get("goods")
                if not goods:
                    errors.append({"goods": "This field is required."})
                else:
                    for good in licence.get("goods"):
                        serializer = GoodSerializer(data=good)
                        if not serializer.is_valid():
                            errors.append({"goods": serializer.errors})

        if errors:
            return JsonResponse(status=status.HTTP_400_BAD_REQUEST, data={"errors": errors})
        else:
            licence, created = LicencePayload.objects.get_or_create(
                lite_id=licence["id"],
                reference=licence["reference"],
                action=licence["action"],
                old_lite_id=licence.get("old_id"),
                old_reference=licence.get("old_reference"),
                defaults=dict(
                    lite_id=licence["id"],
                    reference=licence["reference"],
                    data=licence,
                    old_lite_id=licence.get("old_id"),
                    old_reference=licence.get("old_reference"),
                ),
            )

            logging.info(f"Created LicencePayload [{licence.lite_id}, {licence.reference}, {licence.action}]")

            return JsonResponse(
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK, data={"licence": licence.data},
            )


class ManageInbox(APIView):
    def get(self, request):
        manage_inbox.now()

        return HttpResponse(status=HTTP_200_OK)


class SendLicenceUpdatesToHmrc(APIView):
    def get(self, request):
        send_licence_updates_to_hmrc.now()

        return HttpResponse(status=HTTP_200_OK)


class SendUsageUpdatesToLiteApi(APIView):
    def get(self, request):
        usage_update = UsageUpdate.objects.last()
        send_licence_usage_figures_to_lite_api.now(str(usage_update.id))

        return HttpResponse(status=HTTP_200_OK)
