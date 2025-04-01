import uuid

import pytest

from mail.enums import LicenceActionEnum


@pytest.fixture()
def fa_oil_insert_payload():
    return {
        "type": "OIL",
        "action": "insert",
        "id": "deaa301d-d978-473b-b76b-da275f28f447",
        "reference": "IMA/2022/00001",
        "licence_reference": "GBOIL2222222C",
        "start_date": "2022-06-06",
        "end_date": "2025-05-30",
        "organisation": {
            "eori_number": "GB112233445566000",
            "name": "org name",
            "address": {
                "line_1": "line_1",
                "line_2": "line_2",
                "line_3": "line_3",
                "line_4": "line_4",
                "line_5": "line_5",
                "postcode": "S118ZZ",  # /PS-IGNORE
            },
        },
        "country_group": "G001",
        "restrictions": "Some restrictions.\nSome more restrictions",
        "goods": [
            {
                "description": (
                    "Firearms, component parts thereof, or ammunition of"
                    " any applicable commodity code, other than those"
                    " falling under Section 5 of the Firearms Act 1968"
                    " as amended."
                ),
            }
        ],
    }


@pytest.fixture()
def fa_dfl_insert_payload():
    org_data = {
        "eori_number": "GB665544332211000",
        "name": "DFL Organisation",
        "address": {
            "line_1": "line_1",
            "line_2": "line_2",
            "line_3": "line_3",
            "line_4": "line_4",
            "line_5": "",
            "postcode": "S881ZZ",
        },
    }
    restrictions = "Sample restrictions"

    return {
        "type": "DFL",
        "action": "insert",
        "id": "4277dd90-7ac0-4f48-b228-94c4a2fc61b2",
        "reference": "IMA/2022/00002",
        "licence_reference": "GBSIL1111111C",
        "start_date": "2022-01-14",
        "end_date": "2022-07-14",
        "organisation": org_data,
        "country_code": "US",
        "restrictions": restrictions,
        "goods": [{"description": "Sample goods description"}],
    }


@pytest.fixture
def fa_dfl_insert_payload_2():
    org_data = {
        "eori_number": "GB665544332211000",
        "name": "DFL Organisation",
        "address": {
            "line_1": "line_1",
            "line_2": "line_2",
            "line_3": "line_3",
            "line_4": "line_4",
            "line_5": "",
            "postcode": "S881ZZ",
        },
    }
    restrictions = "Sample restrictions"

    return {
        "type": "DFL",
        "action": "insert",
        "id": "f4142c5a-19f8-40b4-a9a8-46362eaa85c6",
        "reference": "IMA/2022/00003",
        "licence_reference": "GBSIL9089278D",
        "start_date": "2022-01-14",
        "end_date": "2022-07-14",
        "organisation": org_data,
        "country_code": "US",
        "restrictions": restrictions,
        "goods": [{"description": "Sample goods description 2"}],
    }


@pytest.fixture
def fa_sil_insert_payload():
    goods = [
        {
            "description": "Sample goods description 1",
            "quantity": 1,
            "controlled_by": "Q",
            "unit": 30,
        },
        {
            "description": "Sample goods description 2",
            "quantity": 2,
            "controlled_by": "Q",
            "unit": 30,
        },
        {
            "description": "Sample goods description 3",
            "quantity": 3,
            "controlled_by": "Q",
            "unit": 30,
        },
        {
            "description": "Sample goods description 4",
            "quantity": 4,
            "controlled_by": "Q",
            "unit": 30,
        },
        {
            "description": "Sample goods description 5",
            "quantity": 5,
            "controlled_by": "Q",
            "unit": 30,
        },
        {"description": "Unlimited Description goods line", "controlled_by": "O"},
    ]

    return {
        "type": "SIL",
        "action": "insert",
        "id": str(uuid.uuid4()),
        "reference": "IMA/2022/00003",
        "licence_reference": "GBSIL3333333H",
        "start_date": "2022-06-29",
        "end_date": "2024-12-29",
        "organisation": {
            "eori_number": "GB123456654321000",
            "name": "SIL Organisation",
            "address": {
                "line_1": "line_1",
                "line_2": "line_2",
                "line_3": "line_3",
                "line_4": "",
                "line_5": "",
                "postcode": "S227ZZ",
            },
        },
        "country_code": "US",
        "restrictions": "Sample restrictions",
        "goods": goods,
    }


@pytest.fixture
def fa_sil_individual_importer_payload():
    return {
        "type": "SIL",
        "action": "insert",
        "id": str(uuid.uuid4()),
        "reference": "IMA/2022/00003",
        "licence_reference": "GBSIL3333333H",
        "start_date": "2022-06-29",
        "end_date": "2024-12-29",
        "organisation": {
            "eori_number": "GB123451234512345",
            "name": "SIL Organisation",
            "address": {
                "line_1": "line_1",
                "line_2": "line_2",
                "line_3": "line_3",
                "line_4": "",
                "line_5": "",
                "postcode": "S227ZZ",
            },
        },
        "country_code": "US",
        "restrictions": "Sample restrictions",
        "goods": [
            {
                "description": "Sample goods description 1",
                "quantity": 1,
                "controlled_by": "Q",
                "unit": 30,
            },
        ],
    }


@pytest.fixture
def fa_sil_revoke_payload():
    return {
        "action": LicenceActionEnum.CANCEL,
        "reference": "IMA/2023/00001",
        "id": "4f622c3a-88a8-4cb3-8cfc-3090c7daf466",
        "type": "SIL",
        "start_date": "2022-06-29",
        "end_date": "2024-12-29",
        "licence_reference": "GBSIL3333333H",
    }


@pytest.fixture
def sanctions_insert_payload():
    goods = [
        {"commodity": "7214993100", "quantity": 26710, "controlled_by": "Q", "unit": 23},
        {"commodity": "7214997100", "quantity": 48042, "controlled_by": "Q", "unit": 23},
        {"commodity": "7215508000", "quantity": 4952, "controlled_by": "Q", "unit": 23},
    ]

    return {
        "type": "SAN",
        "action": "insert",
        "id": str(uuid.uuid4()),
        "reference": "IMA/2022/00004",
        "licence_reference": "GBSAN4444444A",
        "start_date": "2022-06-29",
        "end_date": "2024-12-29",
        "organisation": {
            "eori_number": "GB112233445566000",
            "name": "Sanction Organisation",
            "address": {
                "line_1": "line_1",
                "line_2": "line_2",
                "line_3": "line_3",
                "line_4": "",
                "line_5": "",
                "postcode": "S227ZZ",
            },
        },
        "country_code": "RU",
        "restrictions": "",
        "goods": goods,
    }


@pytest.fixture
def nuclear_insert_payload():
    goods = [
        {
            "commodity": "2612101000",
            "description": "Goods description 1",
            "controlled_by": "Q",
            "unit": 21,
            "quantity": 12345.0,
        },
        {
            "commodity": "2844306100",
            "description": "Goods description 2",
            "controlled_by": "Q",
            "unit": 23,
            "quantity": 22222.0,
        },
        {
            "commodity": "2844305190",
            "description": "Goods description 3",
            "controlled_by": "Q",
            "unit": 76,
            "quantity": 33333.0,
        },
        {
            "commodity": "2844500000",
            "description": "Goods description 4",
            "controlled_by": "Q",
            "unit": 116,
            "quantity": 44444.0,
        },
        {
            "commodity": "2844306900",
            "description": "Goods description 5",
            "controlled_by": "Q",
            "unit": 74,
            "quantity": 55555.0,
        },
        {"commodity": "2844209900", "description": "Goods description 6", "controlled_by": "O"},
    ]

    return {
        "type": "NUCLEAR",
        "action": "insert",
        "id": str(uuid.uuid4()),
        "reference": "IMA/2025/00001",
        "licence_reference": "GBSIL0000001B",
        "start_date": "2025-03-31",
        "end_date": "2026-03-31",
        "organisation": {
            "eori_number": "GB112233445566000",
            "name": "Nuclear Organisation",
            "address": {
                "line_1": "line_1",
                "line_2": "line_2",
                "line_3": "line_3",
                "line_4": "",
                "line_5": "",
                "postcode": "S227ZZ",
            },
        },
        "country_code": "RU",
        "restrictions": "",
        "goods": goods,
    }
