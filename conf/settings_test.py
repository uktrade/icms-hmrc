from conf.settings import *  # noqa: F401, F403

HAWK_AUTHENTICATION_ENABLED = False

# INCOMING_EMAIL_XXX settings are used when processing licenceReply and usageData emails
# POP3 email settings (to fetch emails from HMRC)
INCOMING_EMAIL_HOSTNAME = "localhost"
INCOMING_EMAIL_USER = "test_user"
INCOMING_EMAIL_POP3_PORT = "995"

# Speed up tests - https://docs.djangoproject.com/en/3.0/topics/testing/overview/#password-hashing
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
