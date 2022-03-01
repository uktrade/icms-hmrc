import email.encoders
import logging
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import json

from unidecode import unidecode

from django.conf import settings
from django.core import mail
from django.utils import timezone

from mail.enums import SourceEnum, ExtractTypeEnum
from mail.libraries.combine_usage_replies import combine_lite_and_spire_usage_responses
from mail.libraries.email_message_dto import EmailMessageDto
from mail.libraries.helpers import convert_source_to_sender
from mail.libraries.lite_to_edifact_converter import licences_to_edifact
from mail.libraries.usage_data_decomposition import split_edi_data_by_id, build_edifact_file_from_data_blocks
from mail.models import LicenceData, Mail, UsageData


def build_request_mail_message_dto(mail: Mail) -> EmailMessageDto:
    sender = None
    receiver = None
    attachment = [None, None]
    run_number = 0
    if mail.extract_type == ExtractTypeEnum.LICENCE_DATA:
        sender = settings.INCOMING_EMAIL_USER
        receiver = settings.OUTGOING_EMAIL_USER
        licence_data = LicenceData.objects.get(mail=mail)
        run_number = licence_data.hmrc_run_number
        attachment = [
            build_sent_filename(mail.edi_filename, run_number),
            build_sent_file_data(mail.edi_data, run_number),
        ]
    elif mail.extract_type == ExtractTypeEnum.USAGE_DATA:
        sender = settings.HMRC_ADDRESS
        receiver = settings.SPIRE_ADDRESS
        update = UsageData.objects.get(mail=mail)
        run_number = update.spire_run_number
        spire_data, _ = split_edi_data_by_id(mail.edi_data)
        if len(spire_data) > 2:  # if SPIRE blocks contain more than just a header & footer
            file = build_edifact_file_from_data_blocks(spire_data)
            attachment = [
                build_sent_filename(mail.edi_filename, run_number),
                build_sent_file_data(file, run_number),
            ]

    logging.info(
        f"Preparing request Mail dto of extract type {mail.extract_type}, sender {sender}, receiver {receiver} with filename {attachment[0]}"
    )

    return EmailMessageDto(
        run_number=run_number,
        sender=sender,
        receiver=receiver,
        date=datetime.now(),
        subject=attachment[0],
        body=None,
        attachment=attachment,
        raw_data=None,
    )


def _build_request_mail_message_dto_internal(mail: Mail) -> EmailMessageDto:
    sender = None
    receiver = None
    attachment = [None, None]
    run_number = 0

    if mail.extract_type == ExtractTypeEnum.LICENCE_DATA:
        """
        This is the case where we sent a licence_data email earlier which hasn't reached HMRC
        and so we are resending it
        """
        sender = settings.EMAIL_USER
        receiver = settings.OUTGOING_EMAIL_USER
        attachment = [mail.sent_filename, mail.sent_data]
    elif mail.extract_type == ExtractTypeEnum.LICENCE_REPLY:
        """
        This is the case where we sent the licence_reply email to SPIRE but they haven't
        received it and so we are resending it
        """
        sender = settings.EMAIL_USER
        receiver = settings.SPIRE_ADDRESS
        attachment = [mail.sent_response_filename, mail.sent_response_data]
    elif mail.extract_type == ExtractTypeEnum.USAGE_DATA:
        sender = settings.EMAIL_USER
        receiver = settings.SPIRE_ADDRESS
        update = UsageData.objects.get(mail=mail)
        run_number = update.spire_run_number
        spire_data, _ = split_edi_data_by_id(mail.edi_data)
        if len(spire_data) > 2:  # if SPIRE blocks contain more than just a header & footer
            file = build_edifact_file_from_data_blocks(spire_data)
            attachment = [
                build_sent_filename(mail.edi_filename, run_number),
                build_sent_file_data(file, run_number),
            ]
    else:
        return None

    logging.info(
        f"Preparing request Mail dto of extract type {mail.extract_type}, sender {sender}, receiver {receiver} with filename {attachment[0]}"
    )

    return EmailMessageDto(
        run_number=run_number,
        sender=sender,
        receiver=receiver,
        date=datetime.now(),
        subject=attachment[0],
        body=None,
        attachment=attachment,
        raw_data=None,
    )


def build_sent_filename(filename: str, run_number: int) -> str:
    filename = filename.split("_")
    filename[4] = str(run_number)
    return "_".join(filename)


def build_sent_file_data(file_data: str, run_number: int) -> str:
    file_data_lines = file_data.split("\n", 1)

    file_data_line_1 = file_data_lines[0]
    file_data_line_1 = file_data_line_1.split("\\")
    file_data_line_1[6] = str(run_number)
    file_data_line_1 = "\\".join(file_data_line_1)

    return file_data_line_1 + "\n" + file_data_lines[1]


def build_reply_mail_message_dto(mail) -> EmailMessageDto:
    sender = settings.HMRC_ADDRESS
    receiver = settings.SPIRE_ADDRESS
    run_number = None

    if mail.extract_type == ExtractTypeEnum.LICENCE_DATA:
        licence_data = LicenceData.objects.get(mail=mail)
        run_number = licence_data.source_run_number
        receiver = convert_source_to_sender(licence_data.source)
        logging.info(
            f"[{mail.extract_type}] Source {licence_data.source} run number: {run_number}, HMRC run number: {licence_data.hmrc_run_number}"
        )
    elif mail.extract_type == ExtractTypeEnum.LICENCE_REPLY:
        licence_data = LicenceData.objects.get(mail=mail)
        run_number = licence_data.source_run_number
        receiver = convert_source_to_sender(licence_data.source)
        logging.info(
            f"[{mail.extract_type}] Source {licence_data.source} run number: {run_number}, HMRC run number: {licence_data.hmrc_run_number}"
        )
    elif mail.extract_type == ExtractTypeEnum.USAGE_DATA:
        usage_data = UsageData.objects.get(mail=mail)
        run_number = usage_data.hmrc_run_number
        sender = settings.SPIRE_ADDRESS
        receiver = settings.HMRC_ADDRESS
        mail.response_data = combine_lite_and_spire_usage_responses(mail)

    attachment = [
        build_sent_filename(mail.response_filename, run_number),
        build_sent_file_data(mail.response_data, run_number),
    ]

    logging.info(
        f"Preparing reply Mail dto of extract type {mail.extract_type}, sender {sender}, receiver {receiver} with filename {attachment[0]}"
    )

    return EmailMessageDto(
        run_number=run_number,
        sender=sender,
        receiver=receiver,
        subject=attachment[0],
        date=datetime.now(),
        body=None,
        attachment=attachment,
        raw_data=None,
    )


def build_licence_data_mail(licences) -> Mail:
    last_lite_update = LicenceData.objects.last()
    run_number = last_lite_update.hmrc_run_number + 1 if last_lite_update else 1
    file_name, file_content = build_licence_data_file(licences, run_number)
    mail = Mail.objects.create(
        edi_filename=file_name,
        edi_data=file_content,
        extract_type=ExtractTypeEnum.LICENCE_DATA,
        raw_data="See Licence Payload",
    )
    logging.info(f"New Mail instance ({mail.id}) created for filename {file_name}")
    licence_ids = json.dumps([licence.reference for licence in licences])
    LicenceData.objects.create(hmrc_run_number=run_number, source=SourceEnum.LITE, mail=mail, licence_ids=licence_ids)

    return mail


def build_licence_data_file(licences, run_number) -> (str, str):
    now = timezone.now()
    file_name = "CHIEF_LIVE_SPIRE_licenceData_{}_{:04d}{:02d}{:02d}{:02d}{:02d}".format(
        run_number, now.year, now.month, now.day, now.hour, now.minute
    )
    logging.info(f"Building licenceData file {file_name} for {len(licences)} licences")

    file_content = licences_to_edifact(licences, run_number)

    return file_name, file_content


def build_email_message(email_message_dto: EmailMessageDto) -> mail.EmailMessage:
    """Make a Django EmailMessage, with the data as a 7-bit attachment."""
    _validate_dto(email_message_dto)
    filename, content = email_message_dto.attachment
    encoded_content = unidecode(content, errors="replace")

    if content != encoded_content:
        logging.info(
            "File content different after transliteration\nBefore: %r\nAfter: %r", content, encoded_content,
        )

    part1 = MIMEText("\n\n", _charset="iso-8859-1")
    part2 = MIMEApplication(encoded_content, _encoder=email.encoders.encode_7or8bit)
    part2.add_header("Content-Disposition", "attachment", filename=filename)

    message = mail.EmailMessage(
        subject=email_message_dto.subject,
        body="",
        from_email=settings.EMAIL_USER,  # the SMTP server only allows sending as itself
        to=[email_message_dto.receiver],
        attachments=[part1, part2],
    )

    return message


def _validate_dto(email_message_dto):
    if email_message_dto is None:
        raise TypeError("None email_message_dto received!")

    if email_message_dto.attachment is None:
        raise TypeError("None file attachment received!")
