import uuid

from mail.models import LicencePayload


def test_licence_payload_model__str__():
    lite_id = uuid.uuid4()
    lp = LicencePayload(lite_id=lite_id, reference="IMA/2022/00001", action="insert")

    assert f"LicencePayload(lite_id={lite_id}, reference=IMA/2022/00001, action=insert)" == str(lp)
