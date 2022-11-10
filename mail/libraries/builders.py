import datetime
import json
import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING, Tuple

from django.conf import settings
from django.utils import timezone
from unidecode import unidecode

from mail.enums import ExtractTypeEnum, SourceEnum
from mail.libraries.combine_usage_replies import combine_lite_and_spire_usage_responses
from mail.libraries.email_message_dto import EmailMessageDto
from mail.libraries.helpers import convert_source_to_sender
from mail.libraries.lite_to_edifact_converter import licences_to_edifact
from mail.libraries.usage_data_decomposition import build_edifact_file_from_data_blocks, split_edi_data_by_id
from mail.models import LicenceData, Mail, UsageData

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from django.db.models import QuerySet  # noqa

    from mail.models import LicencePayload  # noqa


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

    logger.info(
        "Preparing request Mail dto of extract type %s, sender %s, receiver %s with filename %s",
        mail.extract_type,
        sender,
        receiver,
        attachment[0],
    )

    return EmailMessageDto(
        run_number=run_number,
        sender=sender,
        receiver=receiver,
        date=timezone.now(),
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
        # This is the case where we sent a licence_data email earlier which hasn't reached HMRC
        # and so we are resending it
        sender = settings.EMAIL_USER
        receiver = settings.OUTGOING_EMAIL_USER
        attachment = [mail.sent_filename, mail.sent_data]
    elif mail.extract_type == ExtractTypeEnum.LICENCE_REPLY:
        # This is the case where we sent the licence_reply email to SPIRE but they haven't
        # received it and so we are resending it
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

    logger.info(
        "Preparing request Mail dto of extract type %s, sender %s, receiver %s with filename %s",
        mail.extract_type,
        sender,
        receiver,
        attachment[0],
    )

    return EmailMessageDto(
        run_number=run_number,
        sender=sender,
        receiver=receiver,
        date=timezone.now(),
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
        logger.info(
            "[%s] Source %s run number: %s, HMRC run number: %s",
            mail.extract_type,
            licence_data.source,
            run_number,
            licence_data.hmrc_run_number,
        )
    elif mail.extract_type == ExtractTypeEnum.LICENCE_REPLY:
        licence_data = LicenceData.objects.get(mail=mail)
        run_number = licence_data.source_run_number
        receiver = convert_source_to_sender(licence_data.source)
        logger.info(
            "[%s] Source %s run number: %s, HMRC run number: %s",
            mail.extract_type,
            licence_data.source,
            run_number,
            licence_data.hmrc_run_number,
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

    logger.info(
        "Preparing reply Mail dto of extract type %s, sender %s, receiver %s with filename %s",
        mail.extract_type,
        sender,
        receiver,
        attachment[0],
    )

    return EmailMessageDto(
        run_number=run_number,
        sender=sender,
        receiver=receiver,
        subject=attachment[0],
        date=timezone.now(),
        body=None,
        attachment=attachment,
        raw_data=None,
    )


def build_licence_data_mail(licences: "QuerySet[LicencePayload]", source: SourceEnum) -> Mail:
    last_lite_update = LicenceData.objects.last()
    run_number = last_lite_update.hmrc_run_number + 1 if last_lite_update else 1
    when = timezone.now()
    file_name, file_content = build_licence_data_file(licences, run_number, when)
    mail = Mail.objects.create(
        edi_filename=file_name,
        edi_data=file_content,
        extract_type=ExtractTypeEnum.LICENCE_DATA,
        raw_data="See Licence Payload",
    )
    logger.info("New Mail instance (%s) created for filename %s", mail.id, file_name)
    licence_ids = json.dumps([licence.reference for licence in licences])
    licence_data = LicenceData.objects.create(
        hmrc_run_number=run_number, source=source, mail=mail, licence_ids=licence_ids
    )

    # Keep a reference of all licence_payloads linked to this LicenceData instance
    licence_data.licence_payloads.set(licences)

    return mail


def build_licence_data_file(
    licences: "QuerySet[LicencePayload]", run_number: int, when: datetime.datetime
) -> Tuple[str, str]:
    system = settings.CHIEF_SOURCE_SYSTEM
    file_name = f"CHIEF_LIVE_{system}_licenceData_{run_number}_{when:%Y%m%d%H%M}"
    logger.info("Building licenceData file %s for %s licences", file_name, licences.count())

    file_content = licences_to_edifact(licences, run_number, system, when)

    return file_name, file_content


def build_email_message(email_message_dto: EmailMessageDto) -> MIMEMultipart:
    """Build mail message from EmailMessageDto.
    :param email_message_dto: the DTO object this mail message is built upon
    :return: a multipart message
    """
    _validate_dto(email_message_dto)

    logger.info("Building email message...")
    file = unidecode(email_message_dto.attachment[1], errors="replace")

    if email_message_dto.attachment[1] != file:
        logger.info(
            "File content different after transliteration\nBefore: %s\nAfter: %s\n",
            email_message_dto.attachment[1],
            file,
        )

    multipart_msg = MIMEMultipart()
    multipart_msg["From"] = settings.EMAIL_USER  # the SMTP server only allows sending as itself
    multipart_msg["To"] = email_message_dto.receiver
    multipart_msg["Subject"] = email_message_dto.subject
    multipart_msg["name"] = email_message_dto.subject
    multipart_msg.attach(MIMEText("\n\n", "plain", "iso-8859-1"))
    payload = MIMEApplication(file)
    payload.set_payload(file)
    payload.add_header(
        "Content-Disposition",
        f'attachment; filename="{email_message_dto.attachment[0]}"',
    )
    payload.add_header("Content-Transfer-Encoding", "7bit")
    payload.add_header("name", email_message_dto.subject)
    multipart_msg.attach(payload)
    logger.info("Message headers: %s, Payload headers: %s", multipart_msg.items(), payload.items())
    return multipart_msg


def _validate_dto(email_message_dto):
    if email_message_dto is None:
        raise TypeError("None email_message_dto received!")

    if email_message_dto.attachment is None:
        raise TypeError("None file attachment received!")
