import poplib

from typing_extensions import Protocol


class Authenticator(Protocol):
    user: str

    def authenticate(self, connection: poplib.POP3_SSL):
        ...


class BasicAuthentication:
    def __init__(self, user: str, password: str):
        self.user = user
        self.password = password

    def authenticate(self, connection: poplib.POP3_SSL):
        connection.user(self.user)
        connection.pass_(self.password)

    def __eq__(self, other: Authenticator):
        return self.user == other.user and self.password == other.password
