from django.http import JsonResponse
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

            end_user = licence.get("end_user")
            if not end_user:
                errors.append({"end_user": "This field is required."})
            else:
                serializer = ForiegnTraderSerializer(data=end_user)
                if not serializer.is_valid():
                    errors.append({"end_user": serializer.errors})

            if licence.get("type") in LicenceTypeEnum.STANDARD_LICENCES:
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

            return JsonResponse(
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK, data={"licence": licence.data},
            )
