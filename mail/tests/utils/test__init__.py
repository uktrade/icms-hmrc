import pytest
from django.test import override_settings

from mail.utils import get_app_env


@override_settings(APP_ENV="notset")
def test_foo():
    with pytest.raises(ValueError, match="APP_ENV has not been set"):
        get_app_env()
