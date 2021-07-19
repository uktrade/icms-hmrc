import json

import requests
import psycopg2

url_root = "http://localhost:8000"

def get(url):
    requests.get(url_root + url)


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
    return response.json()['items'][0]['MIME']['Parts'][1]['Body']


def clear_mail_tables():
    connection = psycopg2.connect(user="postgres",
                                  password="password",
                                  host="localhost",
                                  port="5432",
                                  database="postgres")
    cursor = connection.cursor()
    cursor.execute("delete from mail_licencepayload;")
    cursor.execute("delete from mail_licencedata;")
    cursor.execute("delete from mail;")
    connection.commit()
    cursor.close()
    connection.close()


def test_send_license():
    clear_stmp_mailbox()
    clear_mail_tables()
    with open("licence_payload_file.json") as f:
        data = json.load(f)
    post("/mail/update-licence/", data=data)
    get("/mail/send-licence-updates-to-hmrc/")
    body = get_smtp_body().replace("\r", "")
    # Remove the first line as it contains a date that changes every time
    body = "\n".join(body.split("\n")[1:])
    with open("expected_mail_body.txt") as f:
        expected_mail_body = f.read()
    assert body.replace("\r", "") == expected_mail_body
