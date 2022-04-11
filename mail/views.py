import logging

from django.http import HttpResponse, JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_500_INTERNAL_SERVER_ERROR
from rest_framework.views import APIView

from conf.authentication import HawkOnlyAuthentication
from mail.enums import LicenceActionEnum, LicenceTypeEnum, ReceptionStatusEnum
from mail.models import LicenceData, LicenceIdMapping, LicencePayload, Mail, UsageData
from mail.serializers import ForiegnTraderSerializer, GoodSerializer, LiteLicenceDataSerializer, MailSerializer
from mail.tasks import manage_inbox, send_licence_data_to_hmrc, send_licence_usage_figures_to_lite_api


class LicenceDataIngestView(APIView):
    authentication_classes = (HawkOnlyAuthentication,)

    def post(self, request):
        errors = []

        licence = request.data.get("licence")

        if not licence:
            errors.append({"licence": "This field is required."})
        else:
            serializer = LiteLicenceDataSerializer(data=licence)
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
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
                data={"licence": licence.data},
            )


class ManageInbox(APIView):
    def get(self, _):
        manage_inbox.now()
        return HttpResponse(status=HTTP_200_OK)


class SendLicenceUpdatesToHmrc(APIView):
    def get(self, _):
        """
        Force the task of sending licence data to HMRC (I assume for testing?)
        """
        success = send_licence_data_to_hmrc.now()
        if success:
            return HttpResponse(status=HTTP_200_OK)
        else:
            return HttpResponse(status=HTTP_500_INTERNAL_SERVER_ERROR)


class SendUsageUpdatesToLiteApi(APIView):
    def get(self, _):
        usage_data = UsageData.objects.last()
        send_licence_usage_figures_to_lite_api.now(str(usage_data.id))
        return HttpResponse(status=HTTP_200_OK)


class SetAllToReplySent(APIView):
    """
    Updates status of all emails to REPLY_SENT
    """

    def get(self, _):
        Mail.objects.all().update(status=ReceptionStatusEnum.REPLY_SENT)
        return HttpResponse(status=HTTP_200_OK)


class Licence(APIView):
    def get(self, request):
        """
        Fetch existing licence
        """
        license_ref = request.GET.get("id", "")

        matching_licences = LicenceData.objects.filter(licence_ids__contains=license_ref)
        matching_licences_count = matching_licences.count()
        if matching_licences_count > 1:
            logging.warn(f"Too many matches for licence '{license_ref}'")
            return Response(status=status.HTTP_400_BAD_REQUEST)
        elif matching_licences_count == 0:
            logging.warn(f"No matches for licence '{license_ref}'")
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Return single matching licence
        mail = matching_licences.first().mail
        serializer = MailSerializer(mail)
        return JsonResponse(serializer.data)
