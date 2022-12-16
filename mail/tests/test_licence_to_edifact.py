from unittest import mock

from django.utils import timezone
from parameterized import parameterized

from mail.enums import LicenceActionEnum
from mail.libraries.chieftypes import Country
from mail.libraries.lite_to_edifact_converter import (
    EdifactValidationError,
    generate_lines_for_licence,
    get_transaction_reference,
    licences_to_edifact,
)
from mail.models import GoodIdMapping, LicencePayload, Mail
from mail.tasks import send_licence_data_to_hmrc
from mail.tests.libraries.client import LiteHMRCTestClient


class LicenceToEdifactTests(LiteHMRCTestClient):
    @parameterized.expand(["siel", "sitl", "sicl"])
    def test_mappings(self, licence_type):
        licence = LicencePayload.objects.get()
        licence.data["type"] = licence_type
        licence.save()
        organisation_id = licence.data["organisation"]["id"]
        good_id = licence.data["goods"][0]["id"]

        licences_to_edifact(LicencePayload.objects.filter(), 1234, "FOO")

        self.assertEqual(
            GoodIdMapping.objects.filter(lite_id=good_id, line_number=1, licence_reference=licence.reference).count(), 1
        )

    def test_single_siel(self):
        licences = LicencePayload.objects.filter(is_processed=False)

        result = licences_to_edifact(licences, 1234, "FOO")
        trader = licences[0].data["organisation"]
        now = timezone.now()
        expected = (
            "1\\fileHeader\\FOO\\CHIEF\\licenceData\\"
            + "{:04d}{:02d}{:02d}{:02d}{:02d}".format(now.year, now.month, now.day, now.hour, now.minute)
            + "\\1234\\N"
            + "\n2\\licence\\20200000001P\\insert\\GBSIEL/2020/0000001/P\\SIE\\E\\20200602\\20220602"
            + f"\n3\\trader\\\\{trader['eori_number']}\\20200602\\20220602\\Organisation\\might 248 James Key Apt. 515 Apt.\\942 West Ashleyton Farnborough\\Apt. 942\\West Ashleyton\\Farnborough\\GU40 2LX"
            + "\n4\\country\\GB\\\\D"
            + "\n5\\foreignTrader\\End User\\42 Road, London, Buckinghamshire\\\\\\\\\\\\GB"
            + "\n6\\restrictions\\Provisos may apply please see licence"
            + "\n7\\line\\1\\\\\\\\\\Sporting shotgun\\Q\\\\030\\\\10\\\\\\\\\\\\"
            + "\n8\\end\\licence\\7"
            + "\n9\\fileTrailer\\1\n"
        )

        self.assertEqual(result, expected)

    @mock.patch("mail.tasks.send")
    def test_licence_is_marked_as_processed_after_sending(self, send):
        send.return_value = None
        send_licence_data_to_hmrc.now()

        self.assertEqual(Mail.objects.count(), 1)
        self.single_siel_licence_payload.refresh_from_db()
        self.assertEqual(self.single_siel_licence_payload.is_processed, True)

    @parameterized.expand(
        [
            ("GBSIEL/2020/0000001/P", "20200000001P"),
            ("SIE22-0000025-01", "22000002501"),
        ]
    )
    def test_extract_reference(self, licence_reference, expected_reference):
        self.assertEqual(get_transaction_reference(licence_reference), expected_reference)

    def test_invalid_licence_reference_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_transaction_reference("SIE-INVALID-REF")

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
            old_lite_id=lp.lite_id,
            old_reference=lp.reference,
        )
        licences = LicencePayload.objects.filter(is_processed=False)
        result = licences_to_edifact(licences, 1234, "FOO")

        trader = licences[0].data["organisation"]
        now = timezone.now()
        expected = (
            "1\\fileHeader\\FOO\\CHIEF\\licenceData\\"
            + "{:04d}{:02d}{:02d}{:02d}{:02d}".format(now.year, now.month, now.day, now.hour, now.minute)
            + "\\1234\\N"
            + "\n2\\licence\\20200000001P\\cancel\\GBSIEL/2020/0000001/P\\SIE\\E\\20200602\\20220602"
            + "\n3\\end\\licence\\2"
            + "\n4\\licence\\20200000001Pa\\insert\\GBSIEL/2020/0000001/P/a\\SIE\\E\\20200602\\20220703"
            + f"\n5\\trader\\\\{trader['eori_number']}\\20200602\\20220703\\Organisation\\might 248 James Key Apt. 515 Apt.\\942 West Ashleyton Farnborough\\Apt. 942\\West Ashleyton\\Farnborough\\GU40 2LX"
            + "\n6\\country\\GB\\\\D"
            + "\n7\\foreignTrader\\End User\\42 Road, London, Buckinghamshire\\\\\\\\\\\\GB"
            + "\n8\\restrictions\\Provisos may apply please see licence"
            + "\n9\\line\\1\\\\\\\\\\Sporting shotgun\\Q\\\\030\\\\15\\\\\\\\\\\\"
            + "\n10\\end\\licence\\7"
            + "\n11\\fileTrailer\\2\n"
        )

        self.assertEqual(result, expected)

    def test_cancel(self):
        self.single_siel_licence_payload.action = LicenceActionEnum.CANCEL
        self.single_siel_licence_payload.save()

        licences = LicencePayload.objects.filter(is_processed=False)

        result = licences_to_edifact(licences, 1234, "FOO")

        now = timezone.now()
        expected = (
            "1\\fileHeader\\FOO\\CHIEF\\licenceData\\"
            + "{:04d}{:02d}{:02d}{:02d}{:02d}".format(now.year, now.month, now.day, now.hour, now.minute)
            + "\\1234\\N"
            + "\n2\\licence\\20200000001P\\cancel\\GBSIEL/2020/0000001/P\\SIE\\E\\20200602\\20220602"
            + "\n3\\end\\licence\\2"
            + "\n4\\fileTrailer\\1\n"
        )

        self.assertEqual(result, expected)

    def test_edifact_gen_raises_exception_on_errors(self):
        licence = LicencePayload.objects.get()
        licence.data["type"] = "INVALID_TYPE"
        licence.save()

        with self.assertRaises(EdifactValidationError) as context:
            licences_to_edifact(LicencePayload.objects.filter(is_processed=False), 1234, "FOO")

    @parameterized.expand(
        [
            (
                "50 Industrial Estate\nVery long address line_2 exceeding 35 chars\nVery long address line_3 exceeding 35 chars\nQueensland\nNSW 42551",
                "5\\foreignTrader\\Advanced Firearms Limited\\50 Industrial Estate Very long\\address line_2 exceeding 35 chars\\Very long address line_3 exceeding\\35 chars Queensland NSW 42551\\\\\\GB",
            ),
            (
                "50\nIndustrial\nEstate\nQueensland\nNSW 42551",
                "5\\foreignTrader\\Advanced Firearms Limited\\50 Industrial Estate Queensland NSW\\42551\\\\\\\\\\GB",
            ),
            (
                "50\nIndustrial\nEstate#\nQueensland#\nNSW 42551",
                "5\\foreignTrader\\Advanced Firearms Limited\\50 Industrial Estate Queensland NSW\\42551\\\\\\\\\\GB",
            ),
        ]
    )
    def test_foreign_trader_address_sanitize(self, address_line_1, expected_trader_line):
        lp = LicencePayload.objects.get()
        lp.is_processed = True
        lp.save()
        payload = self.licence_payload_json.copy()
        payload["licence"]["end_user"]["name"] = "Advanced Firearms Limited"
        payload["licence"]["end_user"]["address"]["line_1"] = address_line_1
        LicencePayload.objects.create(
            reference="GBSIEL/2021/0000001/P",
            data=payload["licence"],
            action=LicenceActionEnum.INSERT,
            lite_id="00000000-0000-0000-0000-9792333e8cc8",
        )
        licences = LicencePayload.objects.filter(is_processed=False)
        edifact_file = licences_to_edifact(licences, 1234, "FOO")

        foreign_trader_line = edifact_file.split("\n")[4]
        self.assertEqual(foreign_trader_line, expected_trader_line)

    @parameterized.expand(
        [
            (
                "TEST12345 IFailedTooLong Ltd - Registered address",
                "BIGMAM MANOR",
                "NEW TESCO LANE",
                "HARROW",
                "MIDDLESEX",
                "3\\trader\\\\GB123456789000\\20200602\\20220602\\Advanced Firearms Limited\\TEST12345 IFailedTooLong Ltd -\\Registered address BIGMAM MANOR NEW\\TESCO LANE HARROW MIDDLESEX\\HARROW\\MIDDLESEX\\GU40 2LX",
            ),
            (
                "TEST12345",
                "BIGMAM MANOR IFailedTooLong Ltd - Registered address",
                "NEW TESCO LANE",
                "HARROW",
                "MIDDLESEX",
                "3\\trader\\\\GB123456789000\\20200602\\20220602\\Advanced Firearms Limited\\TEST12345 BIGMAM MANOR\\IFailedTooLong Ltd - Registered\\address NEW TESCO LANE HARROW\\MIDDLESEX\\MIDDLESEX\\GU40 2LX",
            ),
            (
                "TEST12345",
                "BIGMAM MANOR",
                "NEW TESCO LANE - IFailedTooLong Ltd - Registered address",
                "HARROW",
                "MIDDLESEX",
                "3\\trader\\\\GB123456789000\\20200602\\20220602\\Advanced Firearms Limited\\TEST12345 BIGMAM MANOR NEW TESCO\\LANE - IFailedTooLong Ltd -\\Registered address HARROW MIDDLESEX\\HARROW\\MIDDLESEX\\GU40 2LX",
            ),
            (
                "TEST12345 - IFailedTooLong Ltd - Registered address",
                "BIGMAM MANOR - IFailedTooLong Ltd - Registered address",
                "NEW TESCO LANE - IFailedTooLong Ltd - Registered address",
                "HARROW - IFailedTooLong Ltd - Registered address",
                "MIDDLESEX - IFailedTooLong Ltd - Registered address",
                "3\\trader\\\\GB123456789000\\20200602\\20220602\\Advanced Firearms Limited\\TEST12345 - IFailedTooLong Ltd -\\Registered address BIGMAM MANOR -\\IFailedTooLong Ltd - Registered\\address NEW TESCO LANE -\\IFailedTooLong Ltd - Registered\\GU40 2LX",
            ),
            (
                "this is short address",
                "BIGMAM MANOR",
                "NEW TESCO LANE",
                "HARROW",
                "MIDDLESEX",
                "3\\trader\\\\GB123456789000\\20200602\\20220602\\Advanced Firearms Limited\\this is short address BIGMAM MANOR\\NEW TESCO LANE HARROW MIDDLESEX\\NEW TESCO LANE\\HARROW\\MIDDLESEX\\GU40 2LX",
            ),
        ]
    )
    def test_trader_address_sanitize(
        self, address_line_1, address_line_2, address_line_3, address_line_4, address_line_5, expected_trader_line
    ):
        lp = LicencePayload.objects.get()
        lp.is_processed = True
        lp.save()
        payload = self.licence_payload_json.copy()
        payload["licence"]["organisation"]["name"] = "Advanced Firearms Limited"
        payload["licence"]["organisation"]["address"]["line_1"] = address_line_1
        payload["licence"]["organisation"]["address"]["line_2"] = address_line_2
        payload["licence"]["organisation"]["address"]["line_3"] = address_line_3
        payload["licence"]["organisation"]["address"]["line_4"] = address_line_4
        payload["licence"]["organisation"]["address"]["line_5"] = address_line_5
        LicencePayload.objects.create(
            reference="GBSIEL/2021/0000001/P",
            data=payload["licence"],
            action=LicenceActionEnum.INSERT,
            lite_id="00000000-0000-0000-0000-9792333e8cc8",
        )
        licences = LicencePayload.objects.filter(is_processed=False)

        edifact_file = licences_to_edifact(licences, 1234, "FOO")
        trader_line = edifact_file.split("\n")[2]
        self.assertEqual(trader_line, expected_trader_line)


class GenerateLinesForLicenceTest(LiteHMRCTestClient):
    def test_open_licence_with_country_group(self):
        data = {
            "start_date": "1",
            "end_date": "2",
            "organisation": {
                "address": {"line_1": "Required line 1 address"},
            },
            "address": {},
            "type": "oiel",  # One of the OPEN_LICENCES.
            "country_group": "G012",  # This example is from an ICMS message.
        }
        licence = LicencePayload(reference="GBSIEL/123", data=data)
        lines = list(generate_lines_for_licence(licence))

        expected_types = ["licence", "trader", "country", "restrictions", "line", "end"]
        self.assertEqual([line.type_ for line in lines], expected_types)
        # The country code is the 3rd field, `group`.
        self.assertEqual(lines[2], Country(code=None, group="G012", use="D"))

    def test_open_licence_with_multiple_countries(self):
        data = {
            "start_date": "1",
            "end_date": "2",
            "organisation": {
                "address": {"line_1": "Required line 1 address"},
            },
            "address": {},
            "type": "oiel",  # One of the OPEN_LICENCES.
            "countries": [{"id": "GB"}, {"id": "NI"}],
        }
        licence = LicencePayload(reference="GBSIEL/123", data=data)
        lines = list(generate_lines_for_licence(licence))

        # Note there are 2 country lines.
        expected_types = ["licence", "trader", "country", "country", "restrictions", "line", "end"]
        self.assertEqual([line.type_ for line in lines], expected_types)
        # The country code is the 2nd field, `code`.
        self.assertEqual(lines[2], Country(code="GB", group=None, use="D"))
        self.assertEqual(lines[3], Country(code="NI", group=None, use="D"))
