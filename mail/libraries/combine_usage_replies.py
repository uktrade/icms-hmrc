from django.utils import timezone

from mail.models import GoodIdMapping, LicenceIdMapping, TransactionMapping, UsageData


def combine_lite_and_spire_usage_responses(mail) -> str:  # noqa
    usage_data = UsageData.objects.get(mail=mail)
    lite_response = usage_data.lite_response
    spire_response = mail.response_data
    edi_lines = mail.edi_data.split("\n")

    edifact_file = ""
    i = 1

    if spire_response:
        spire_lines = spire_response.split("\n")

        for line in spire_lines:
            if "fileTrailer" in line:
                break
            edifact_file += line + "\n"
            i += 1
    else:
        now = timezone.now()
        time_stamp = "{:04d}{:02d}{:02d}{:02d}{:02d}".format(now.year, now.month, now.day, now.hour, now.minute)
        mail.response_filename = "SPIRE_live_CHIEF_usageReply_<run-number>_{}".format(time_stamp)
        mail.save()
        edifact_file = "1\\fileHeader\\SPIRE\\CHIEF\\usageReply\\{}\\<run-number>\n".format(time_stamp)

    if lite_response:
        if lite_response.get("licences").get("accepted"):
            for licence in lite_response.get("licences").get("accepted"):
                if licence.get("goods"):
                    for good in licence.get("goods"):
                        licence_reference = LicenceIdMapping.objects.get(lite_id=licence["id"]).reference
                        good_mapping = GoodIdMapping.objects.get(
                            licence_reference=licence_reference, lite_id=good["id"]
                        )
                        transaction_id = TransactionMapping.objects.get(
                            licence_reference=licence_reference,
                            line_number=good_mapping.line_number,
                            usage_data=usage_data,
                        ).usage_transaction
                        edifact_file += "{}\\accepted\\{}\n".format(i, transaction_id)
                        i += 1
                        break
                else:
                    licence_reference = LicenceIdMapping.objects.get(lite_id=licence["id"]).reference
                    transaction_id = TransactionMapping.objects.get(
                        licence_reference=licence_reference,
                        line_number=None,
                        usage_data=usage_data,
                    ).usage_transaction
                    edifact_file += "{}\\accepted\\{}\n".format(i, transaction_id)
                    i += 1

        if lite_response.get("licences").get("rejected"):
            for licence in lite_response.get("licences").get("rejected"):
                for good in licence.get("goods").get("rejected"):
                    licence_reference = LicenceIdMapping.objects.get(lite_id=licence["id"]).reference
                    good_mapping = GoodIdMapping.objects.get(licence_reference=licence_reference, lite_id=good["id"])
                    transaction = TransactionMapping.objects.get(
                        licence_reference=licence_reference,
                        line_number=good_mapping.line_number,
                        usage_data=usage_data,
                    )
                    transaction_id = transaction.usage_transaction
                    start_line = i - 1
                    edifact_file += "{}\\rejected\\{}\n".format(i, transaction_id)
                    i += 1
                    error_text = good["errors"]["id"][0] + " in line "
                    j = 0
                    correct_transaction = False
                    error_line = ""
                    for line in edi_lines:
                        j += 1
                        if "licenceUsage" in line:
                            if transaction_id in line:
                                correct_transaction = True
                            else:
                                correct_transaction = False

                        if "line" in line and correct_transaction:
                            if line.split("\\")[2] == str(transaction.line_number):
                                error_line = str(j)

                    edifact_file += "{}\\error\\{}\\{}\n".format(i, i, error_text + error_line)
                    i += 1
                    edifact_file += "{}\\end\\rejected\\{}\n".format(i, i - start_line)
                    i += 1
                    break

    file_trailer = "{}\\fileTrailer\\{}\\{}\\{}".format(
        i,
        edifact_file.count("accepted"),
        int(edifact_file.count("rejected") // 2),
        int(edifact_file.count("fileError") // 2),
    )
    edifact_file += file_trailer
    return edifact_file
