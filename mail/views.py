import logging

from django.http import JsonResponse, HttpResponse
from rest_framework import status
from rest_framework.views import APIView

from conf.authentication import HawkOnlyAuthentication
from mail.enums import LicenceTypeEnum
from mail.models import LicencePayload
from mail.serializers import (
    LiteLicenceUpdateSerializer,
    ForiegnTraderSerializer,
    GoodSerializer,
)
from mail.tasks import manage_inbox
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

            if licence.get("type") in LicenceTypeEnum.OPEN_LICENCES:
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
                defaults=dict(lite_id=licence["id"], reference=licence["reference"], data=licence),
            )

            logging.info(f"Created LicencePayload [{licence.lite_id}, {licence.reference}]")

            return JsonResponse(
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK, data={"licence": licence.data},
            )


class ManageInbox(APIView):
    def get(self, request):
        manage_inbox.now()

        return HttpResponse(status=HTTP_200_OK)
