from unittest import mock

from django.test import tag
from django.utils import timezone

from mail.enums import LicenceActionEnum
from mail.libraries.lite_to_edifact_converter import licences_to_edifact, get_transaction_reference
from mail.models import LicencePayload, Mail, OrganisationIdMapping, GoodIdMapping
from mail.tasks import send_licence_updates_to_hmrc
from mail.tests.libraries.client import LiteHMRCTestClient


class LicenceToEdifactTests(LiteHMRCTestClient):
    @tag("mapping-ids")
    def test_mappings(self):
        licence = LicencePayload.objects.get()

        organisation_id = licence.data["organisation"]["id"]
        good_id = licence.data["goods"][0]["id"]

        licences_to_edifact(LicencePayload.objects.filter(), 1234)

        self.assertEqual(OrganisationIdMapping.objects.filter(lite_id=organisation_id).count(), 1)
        self.assertEqual(
            GoodIdMapping.objects.filter(lite_id=good_id, line_number=1, licence_reference=licence.reference).count(), 1
        )

    @tag("edifact")
    def test_single_siel(self):
        licences = LicencePayload.objects.filter(is_processed=False)

        result = licences_to_edifact(licences, 1234)
        trader = licences[0].data["organisation"]
        org_mapping, _ = OrganisationIdMapping.objects.get_or_create(
            lite_id=trader["id"], defaults={"lite_id": trader["id"]}
        )
        now = timezone.now()
        expected = (
            "1\\fileHeader\\SPIRE\\CHIEF\\licenceData\\"
            + "{:04d}{:02d}{:02d}{:02d}{:02d}".format(now.year, now.month, now.day, now.hour, now.minute)
            + "\\1234"
            + "\n2\\licence\\SIEL20200000001\\insert\\GBSIEL/2020/0000001/P\\siel\\E\\20200602\\20220602"
            + f"\n3\\trader\\\\{org_mapping.rpa_trader_id}\\20200602\\20220602\\Organisation\\might\\248 James Key Apt. 515\\Apt. 942\\West Ashleyton\\Tennessee\\99580"
            + "\n4\\foreignTrader\\End User\\42 Road, London, Buckinghamshire\\\\\\\\\\\\GB"
            + "\n5\\restrictions\\Provisos may apply please see licence"
            + "\n6\\line\\1\\\\\\\\\\finally\\Q\\30\\10"
            + "\n7\\end\\licence\\6"
            + "\n8\\fileTrailer\\1"
        )

        self.assertEqual(result, expected)

    @tag("sending")
    @mock.patch("mail.tasks.send")
    def test_licence_is_marked_as_processed_after_sending(self, send):
        send.return_value = None
        send_licence_updates_to_hmrc.now()

        self.assertEqual(Mail.objects.count(), 1)
        self.single_siel_licence_payload.refresh_from_db()
        self.assertEqual(self.single_siel_licence_payload.is_processed, True)

    @tag("ref")
    def test_ref(self):
        self.assertEqual(get_transaction_reference("GBSIEL/2020/0000001/P"), "SIEL20200000001")

    @tag("update")
    def test_update_edifact_file(self):
        lp = LicencePayload.objects.get()
        lp.is_processed = True
        lp.save()
        payload = self.licence_payload_json.copy()
        payload["licence"]["goods"][0]["quantity"] = 15.0
        payload["licence"]["end_date"] = "2022-07-03"
        payload["licence"]["reference"] = "GBSIEL/2020/0000001/P/a"
        LicencePayload.objects.create(
            reference="GBSIEL/2020/0000001/P/a",
            data=payload["licence"],
            action=LicenceActionEnum.UPDATE,
            lite_id="00000000-0000-0000-0000-9792333e8cc8",
        )
        licences = LicencePayload.objects.filter(is_processed=False)
        result = licences_to_edifact(licences, 1234)

        trader = licences[0].data["organisation"]
        org_mapping, _ = OrganisationIdMapping.objects.get_or_create(
            lite_id=trader["id"], defaults={"lite_id": trader["id"]}
        )
        now = timezone.now()
        expected = (
            "1\\fileHeader\\SPIRE\\CHIEF\\licenceData\\"
            + "{:04d}{:02d}{:02d}{:02d}{:02d}".format(now.year, now.month, now.day, now.hour, now.minute)
            + "\\1234"
            + "\n2\\licence\\SIEL20200000001\\cancel\\GBSIEL/2020/0000001/P\\siel\\E\\20200602\\20220602"
            + "\n3\\end\\licence\\2"
            + "\n4\\licence\\SIEL20200000001a\\insert\\GBSIEL/2020/0000001/P/a\\siel\\E\\20200602\\20220703"
            + f"\n5\\trader\\\\{org_mapping.rpa_trader_id}\\20200602\\20220703\\Organisation\\might\\248 James Key Apt. 515\\Apt. 942\\West Ashleyton\\Tennessee\\99580"
            + "\n6\\foreignTrader\\End User\\42 Road, London, Buckinghamshire\\\\\\\\\\\\GB"
            + "\n7\\restrictions\\Provisos may apply please see licence"
            + "\n8\\line\\1\\\\\\\\\\finally\\Q\\30\\15"
            + "\n9\\end\\licence\\6"
            + "\n10\\fileTrailer\\2"
        )

        self.assertEqual(result, expected)

    @tag("cancel")
    def test_cancel(self):
        self.single_siel_licence_payload.action = LicenceActionEnum.CANCEL
        self.single_siel_licence_payload.save()

        licences = LicencePayload.objects.filter(is_processed=False)

        result = licences_to_edifact(licences, 1234)

        now = timezone.now()
        expected = (
            "1\\fileHeader\\SPIRE\\CHIEF\\licenceData\\"
            + "{:04d}{:02d}{:02d}{:02d}{:02d}".format(now.year, now.month, now.day, now.hour, now.minute)
            + "\\1234"
            + "\n2\\licence\\SIEL20200000001\\cancel\\GBSIEL/2020/0000001/P\\siel\\E\\20200602\\20220602"
            + "\n3\\end\\licence\\2"
            + "\n4\\fileTrailer\\1"
        )

        self.assertEqual(result, expected)
