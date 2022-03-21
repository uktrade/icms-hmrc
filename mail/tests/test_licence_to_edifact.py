from unittest import mock

from django.utils import timezone
from parameterized import parameterized

from mail.enums import LicenceActionEnum
from mail.libraries.lite_to_edifact_converter import (
    licences_to_edifact,
    get_transaction_reference,
    EdifactValidationError,
)
from mail.models import LicencePayload, Mail, GoodIdMapping
from mail.tasks import send_licence_data_to_hmrc
from mail.tests.libraries.client import LiteHMRCTestClient
from mail.libraries import edifact_validator


class LicenceToEdifactTests(LiteHMRCTestClient):
    @parameterized.expand(["siel", "sitl", "sicl"])
    def test_mappings(self, licence_type):
        licence = LicencePayload.objects.get()
        licence.data["type"] = licence_type
        licence.save()
        organisation_id = licence.data["organisation"]["id"]
        good_id = licence.data["goods"][0]["id"]

        licences_to_edifact(LicencePayload.objects.filter(), 1234)

        self.assertEqual(
            GoodIdMapping.objects.filter(lite_id=good_id, line_number=1, licence_reference=licence.reference).count(), 1
        )

    def test_single_siel(self):
        licences = LicencePayload.objects.filter(is_processed=False)

        result = licences_to_edifact(licences, 1234)
        trader = licences[0].data["organisation"]
        now = timezone.now()
        expected = (
            "1\\fileHeader\\SPIRE\\CHIEF\\licenceData\\"
            + "{:04d}{:02d}{:02d}{:02d}{:02d}".format(now.year, now.month, now.day, now.hour, now.minute)
            + "\\1234\\N"
            + "\n2\\licence\\20200000001P\\insert\\GBSIEL/2020/0000001/P\\SIE\\E\\20200602\\20220602"
            + f"\n3\\trader\\\\{trader['eori_number']}\\20200602\\20220602\\Organisation\\might\\248 James Key Apt. 515\\Apt. 942\\West Ashleyton\\Farnborough\\GU40 2LX"
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

    def test_ref(self):
        self.assertEqual(get_transaction_reference("GBSIEL/2020/0000001/P"), "20200000001P")

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
        result = licences_to_edifact(licences, 1234)

        trader = licences[0].data["organisation"]
        now = timezone.now()
        expected = (
            "1\\fileHeader\\SPIRE\\CHIEF\\licenceData\\"
            + "{:04d}{:02d}{:02d}{:02d}{:02d}".format(now.year, now.month, now.day, now.hour, now.minute)
            + "\\1234\\N"
            + "\n2\\licence\\20200000001P\\cancel\\GBSIEL/2020/0000001/P\\SIE\\E\\20200602\\20220602"
            + "\n3\\end\\licence\\2"
            + "\n4\\licence\\20200000001Pa\\insert\\GBSIEL/2020/0000001/P/a\\SIE\\E\\20200602\\20220703"
            + f"\n5\\trader\\\\{trader['eori_number']}\\20200602\\20220703\\Organisation\\might\\248 James Key Apt. 515\\Apt. 942\\West Ashleyton\\Farnborough\\GU40 2LX"
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

        result = licences_to_edifact(licences, 1234)

        now = timezone.now()
        expected = (
            "1\\fileHeader\\SPIRE\\CHIEF\\licenceData\\"
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
            licences_to_edifact(LicencePayload.objects.filter(is_processed=False), 1234)

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
        edifact_file = licences_to_edifact(licences, 1234)
        foreign_trader_line = edifact_file.split("\n")[4]
        self.assertEqual(
            foreign_trader_line,
            expected_trader_line,
        )


class LicenceToEdifactValidationTests(LiteHMRCTestClient):
    @parameterized.expand(
        [
            ("1\\fileHeader\\SPIRE\\CHIEF\\licenceData\\202104090304\\96839\\Y", 0),
            ("1\\fileHeader\\SPIRE\\SPIRE\\licenceData\\202104090304\\96839\\Y", 1),
            ("1\\fileHeader\\SPIRE\\CHIEF\\licenceData\\202104090304\\96839", 1),
            ("1\\fileHeaders\\SPIRE\\CHIEF\\licenceUpdate\\202104090304\\96839\\Y", 2),
            ("1\\fileHeader\\SPIRE\\CHIEF\\licenceUpdate\\202104090304\\96839\\T", 2),
        ]
    )
    def test_file_header_validation(self, header, num_errors):
        errors = edifact_validator.validate_file_header(header)
        self.assertEqual(len(errors), num_errors)

    @parameterized.expand(
        [
            ("2\\licence\\20210000006TA\\insert\\GBSIEL/2021/0000006/T/A\\SIE\\E\\20210408\\20220408", 0),
            ("2\\licences\\20210000006TA\\insert\\GBSIEL/2021/0000006/T/A\\SIE\\E\\20210408\\20220408", 1),
            ("2\\licences\\20210000006TA\\add\\GBSIEL/2021/0000006/T/A\\SIE\\E\\20210408\\20220408", 2),
            ("2\\licence\\20210000006TA\\insert\\GBSIEL/2021/0000006/T/A\\SIEL\\E\\20210408\\20220408", 1),
            ("2\\licence\\20210000006TA\\insert\\GBSIEL/2021/0000006/T/A\\SIEL\\T\\20210408\\20220408", 2),
        ]
    )
    def test_licence_transaction_header_validation(self, licence_tx_line, num_errors):
        errors = edifact_validator.validate_licence_transaction_header("licenceData", licence_tx_line)
        self.assertEqual(len(errors), num_errors)

    @parameterized.expand(
        [
            (
                "3\\trader\\\\GB123456789000\\20210408\\20220408\\ABC Test\\Test Location\\windsor house\\\\Windsor\\Surrey\\AB1 2BD",
                0,
            ),
            (
                "3\\traders\\\\GB123456789000\\20210408\\20220408\\ABC Test\\Test Location\\windsor house\\\\Windsor\\Surrey\\AB1 2BD",
                1,
            ),
            (
                "3\\trader\\\\\\20210408\\20220408\\ABC Test\\Test Location\\windsor house\\\\Windsor\\Surrey\\AB1 2BD",
                2,
            ),
            (
                "3\\trader\\\\\\20210408\\20200408\\ABC Test\\Test Location\\windsor house\\\\Windsor\\Surrey\\AB1 2BD",
                3,
            ),
            (
                "3\\trader\\\\GB123456789000\\20210408\\20200408\\ABC Test\\Test Location\\windsor house\\\\Windsor\\Surrey\\Islington",
                2,
            ),
            (
                "3\\trader\\\\GB123456789000\\20210408\\20220408\\Very long organisation name to trigger validation error, max length is 80 characters\\Test Location\\windsor house\\\\Windsor\\Surrey\\AB1 2BD",
                1,
            ),
            (
                "3\\trader\\\\6\\20210408\\20220408\\Very long organisation name to trigger validation error, max length is 80 characters\\This is a very long address line to trigger error\\windsor house\\\\Windsor\\Surrey\\AB1 2BD",
                3,
            ),
            (
                "3\\trader\\\\GB123456789000\\20210408\\20220408\\Very long organisation name to trigger validation error, max length is 80 characters\\This is a very long address line to trigger error\\windsor house\\\\Windsor\\Surrey\\INVALID POSTCODE",
                3,
            ),
        ]
    )
    def test_permitted_trader_validation(self, line, num_errors):
        errors = edifact_validator.validate_permitted_trader(line)
        self.assertEqual(len(errors), num_errors)

    @parameterized.expand(
        [
            ("4\\country\\AU\\\\D", 0),
            ("4\\country\\AU\\", 1),
            ("4\\country\\AU\\\\T", 1),
            ("4\\country_id\\AU\\AU\\D", 2),
        ]
    )
    def test_country_validation(self, line, num_errors):
        errors = edifact_validator.validate_country(line)
        self.assertEqual(len(errors), num_errors)

    @parameterized.expand(
        [
            ("5\\foreignTrader\\Test party\\1234\\\\\\\\\\\\AU", 0),
            ("5\\foreignTrader\\Test party\\1234\\\\\\\\\\", 1),
            ("5\\foreignTraders\\Test party\\1234\\\\\\\\\\\\AU", 1),
            (
                "5\\foreignTrader\\Advanced Firearms Limited\\50 Industrial Estate Very long\\address line_2 exceeding 35 chars\\Very long address line_3 exceeding\\35 chars Queensland NSW 42551\\\\\\GB",
                0,
            ),
            (
                "5\\foreignTrader\\Advanced Firearms Limited\\50 Industrial Estate Very long\\address line_2 exceeding 35 chars\\Very long address line_3 exceeding\\35 chars Queensland NSW 42551 make it longer\\\\\\GB",
                1,
            ),
            (
                "5\\foreignTrader\\Advanced Firearms Limited\\50 Industrial Estate Very long\\address line_2 exceeding 35 chars\\Very long address line_3 exceeding\\35 chars Queensland NSW 42551\\\\123456789\\GBR",
                2,
            ),
        ]
    )
    def test_foreign_trader_validation(self, line, num_errors):
        errors = edifact_validator.validate_foreign_trader(line)
        self.assertEqual(len(errors), num_errors)

    @parameterized.expand(
        [
            ("6\\restrictions\\Provisos may apply please see licence", 0),
            ("6\\restrictions", 1),
            ("6\\restrictionsline\\Provisos may apply please see licence", 1),
        ]
    )
    def test_restrictions_validation(self, line, num_errors):
        errors = edifact_validator.validate_restrictions(line)
        self.assertEqual(len(errors), num_errors)

    @parameterized.expand(
        [
            ("7\\line\\1\\\\\\\\\\Rifle\\Q\\\\030\\\\4\\\\\\\\\\\\", 0),
            ("7\\line\\1\\\\\\\\\\Rifle\\Q\\\\030\\\\\\\\\\\\\\", 1),
            ("7\\lines\\1\\\\\\\\\\Rifle\\Q\\\\030\\\\4\\\\\\\\\\\\", 1),
            ("7\\line\\1\\\\\\\\\\Rifle\\T\\\\30\\\\4\\\\\\\\\\\\", 2),
            ("7\\lines\\1\\\\\\\\\\\\Q\\\\030\\\\4\\\\\\\\\\\\", 2),
        ]
    )
    def test_licence_product_line_validation(self, line, num_errors):
        errors = edifact_validator.validate_licence_product_line(line)
        self.assertEqual(len(errors), num_errors)

    @parameterized.expand(
        [
            ("10\\end\\licence\\9", 0),
            ("10\\end\\licence", 1),
            ("10\\ending\\licence\\9", 1),
        ]
    )
    def test_end_line_validation(self, line, num_errors):
        errors = edifact_validator.validate_end_line(line)
        self.assertEqual(len(errors), num_errors)

    @parameterized.expand(
        [
            ("11\\fileTrailer\\1", 0),
            ("11\\fileTrailer", 1),
            ("11\\fileTrailers\\1", 1),
        ]
    )
    def test_file_trailer_validation(self, line, num_errors):
        errors = edifact_validator.validate_file_trailer(line)
        self.assertEqual(len(errors), num_errors)
