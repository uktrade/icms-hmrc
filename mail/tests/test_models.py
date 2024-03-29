import uuid

from mail.models import LicencePayload


def test_licence_payload_model__str__():
    icms_id = uuid.uuid4()
    lp = LicencePayload(id=1, icms_id=icms_id, reference="IMA/2022/00001", action="insert")

    assert (
        f"LicencePayload(id=1, icms_id={icms_id}, reference=IMA/2022/00001, action=insert)"
        == str(lp)
    )
