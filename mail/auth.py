import base64
import logging
import poplib
from typing import Protocol

import msal

logger = logging.getLogger(__name__)


class Authenticator(Protocol):
    user: str
    client_id: str
    client_secret: str
    tenant_id: str

    def authenticate(self, connection: poplib.POP3_SSL):
        ...  # fmt: skip


class ModernAuthentication:
    """Uses MS modern authentication (which is OAuth) to authenticate a pop3 connection.

    https://docs.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth
    """

    def __init__(
        self,
        user: str,
        client_id: str,
        client_secret: str,
        tenant_id: str,
    ):
        self.user = user
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id

        authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.app = msal.ConfidentialClientApplication(
            client_id,
            authority=authority,
            client_credential=client_secret,
        )

    def _get_access_token(self):
        scopes = ["https://outlook.office.com/.default"]

        logger.info("Attempting to acquire access token silently")

        # This attempts to get the token from the cache
        result = self.app.acquire_token_silent(scopes, account=None)

        # If we don't find the token in the cache then we go off and retrieve it from the provider
        if not result:
            logger.info("Token not found in cache")
            result = self.app.acquire_token_for_client(scopes=scopes)

        return result["access_token"]

    def _encode_access_string(self, username, access_token):
        return base64.b64encode(
            f"user={username}\x01auth=Bearer {access_token}\x01\x01".encode()
        ).decode()

    def authenticate(self, connection: poplib.POP3_SSL):
        logger.info("Authenticating using OAuth authentication: %s", self.user)
        access_token = self._get_access_token()
        access_string = self._encode_access_string(
            self.user,
            access_token,
        )

        # https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth#pop-protocol-exchange
        connection._shortcmd("AUTH XOAUTH2")
        connection._shortcmd(access_string)

    def __eq__(self, other: Authenticator):
        return (
            self.user == other.user
            and self.client_id == other.client_id
            and self.client_secret == other.client_secret
            and self.tenant_id == other.tenant_id
        )
