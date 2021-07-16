import json

import requests

url_root = "http://localhost:8000"

def get(url):
    requests.get(url_root + url)


def post(url, data=None):
    requests.post(url_root + url, json=data)


def test_send_license():
    with open("licence_payload_file.json") as f:
        data = json.load(f)
    post("/mail/update-licence/", data=data)
    get("/mail/send-licence-updates-to-hmrc/")
