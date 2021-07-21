import json
import string
import uuid
import random

import requests


url_root = "http://localhost:8000"


def put(url):
    requests.put(url_root + url)


def post(url, data=None):
    requests.post(url_root + url, json=data)


def clear_stmp_mailbox():
    response = requests.get("http://localhost:8025/api/v2/messages")
    print(response)
    for message in response.json()["items"]:
        id = message["ID"]
        print(f"delete {id}")
        requests.delete(f"http://localhost:8025/api/v1/messages/{id}")


def get_smtp_body():
    response = requests.get("http://localhost:8025/api/v2/messages")
    print(response)
    return response.json()["items"][0]["MIME"]["Parts"][1]["Body"]


def test_send_license():
    clear_stmp_mailbox()
    put("/mail/set-all-to-reply-sent/")
    with open("licence_payload_file.json") as f:
        data = json.load(f)
    data["licence"]["id"] = str(uuid.uuid4())
    data["licence"]["reference"] = f"GBSIEL/2020/{''.join(random.sample(string.ascii_lowercase, 7))}/P"
    post("/mail/update-licence/", data=data)
    put("/mail/send-licence-updates-to-hmrc/")
    body = get_smtp_body().replace("\r", "")
    # Remove the first and second line as it contains data that changes every time
    body = "\n".join(body.split("\n")[2:])
    with open("expected_mail_body.txt") as f:
        expected_mail_body = f.read()
    assert body.replace("\r", "") == expected_mail_body
