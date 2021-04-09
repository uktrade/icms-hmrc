from mail.enums import LicenceActionEnum, LITE_HMRC_LICENCE_TYPE_MAPPING

FILE_HEADER_FIELDS_LEN = 8
LICENCE_TRANSACTION_HEADER_FIELDS_LEN = 9
PERMITTED_TRADER_HEADER_FIELDS_LEN = 13
COUNTRY_FIELDS_LEN = 5
FOREIGN_TRADER_FIELDS_LEN = 10
LICENCE_LINE_FIELDS_LEN = 13
FILE_TRAILER_FIELDS_LEN = 3

VALID_ACTIONS_TO_HMRC = [choice[0] for choice in LicenceActionEnum.choices]
VALID_LICENCE_TYPES = LITE_HMRC_LICENCE_TYPE_MAPPING.values()
ALLOWED_COUNTRY_USE_VALUES = ["D", "E", "O", "P", "R", "S"]
CONTROLLED_BY_VALUES = ["B", "O", "Q", "V"]


def validate_file_header(record):
    errors = []
    tokens = record.split("\\")
    record_type = tokens[1]

    if len(tokens) != FILE_HEADER_FIELDS_LEN:
        errors.append({record_type: f"{record_type} doesn't contain all necessary values"})
        return errors

    if int(tokens[0]) != 1:
        errors.append({record_type: f"{record_type} is not in the first line"})

    if tokens[1] != "fileHeader":
        errors.append({record_type: f"Invalid file header tag {tokens[1]}"})

    if tokens[2] == tokens[3]:
        errors.append({record_type: "Source and destination are the same"})

    if tokens[4] not in ["licenceData", "licenceReply", "usageData", "usageReply"]:
        errors.append({record_type: f"{record_type} contains invalid data identifier"})

    if tokens[7] not in ["Y", "N"]:
        errors.append({record_type: f"{record_type} contains invalid reset run number indicator"})

    return errors


def validate_licence_transaction_header(data_identifier, record):
    errors = []
    tokens = record.split("\\")
    record_type = tokens[1]
    action = tokens[3]

    if len(tokens) != LICENCE_TRANSACTION_HEADER_FIELDS_LEN:
        errors.append({record_type: f"{record_type} doesn't contain all necessary values"})
        return errors

    if tokens[1] != "licence":
        errors.append({record_type: f"Invalid file header tag {tokens[1]}"})

    if data_identifier in ["licenceData"] and action not in VALID_ACTIONS_TO_HMRC:
        errors.append({record_type: f"Invalid action {action} for the data identifier {data_identifier}"})

    if tokens[5] not in VALID_LICENCE_TYPES:
        errors.append({record_type: f"Invalid licence type {tokens[5]} in the record"})

    if tokens[6] != "E":
        errors.append({record_type: "licence transaction header is not of Export type"})

    return errors


def validate_permitted_trader(record):
    errors = []
    tokens = record.split("\\")
    record_type = tokens[1]
    TURN = tokens[2]
    rpa_trader_id = tokens[3]

    if len(tokens) != PERMITTED_TRADER_HEADER_FIELDS_LEN:
        errors.append({record_type: f"{record_type} doesn't contain all necessary values"})
        return errors

    if tokens[1] != "trader":
        errors.append({record_type: f"Invalid file header tag {tokens[1]}"})

    if TURN == "" and rpa_trader_id == "":
        errors.append({record_type: "RPA Trader Id must not be empty when TURN is empty"})

    if int(tokens[5]) < int(tokens[4]):
        errors.append({record_type: "Invalid start and end dates for the licence"})

    return errors


def validate_country(record):
    errors = []
    tokens = record.split("\\")
    record_type = tokens[1]

    if len(tokens) != COUNTRY_FIELDS_LEN:
        errors.append({record_type: f"{record_type} doesn't contain all necessary values"})
        return errors

    if tokens[1] != "country":
        errors.append({record_type: f"Invalid file header tag {tokens[1]}"})

    if tokens[2] and tokens[3]:
        errors.append({record_type: "Both country code and group cannot be valid in the same record"})

    if tokens[4] not in ALLOWED_COUNTRY_USE_VALUES:
        errors.append({record_type: f"Invalid country use value {tokens[4]}"})

    return errors


def validate_foreign_trader(record):
    errors = []
    tokens = record.split("\\")
    record_type = tokens[1]

    if len(tokens) != FOREIGN_TRADER_FIELDS_LEN:
        errors.append({record_type: f"{record_type} doesn't contain all necessary values"})
        return errors

    if tokens[1] != "foreignTrader":
        errors.append({record_type: f"Invalid file header tag {tokens[1]}"})

    return errors


def validate_restrictions(record):
    errors = []
    tokens = record.split("\\")
    record_type = tokens[1]

    if len(tokens) != 3:
        errors.append({record_type: f"{record_type} doesn't contain all necessary values"})
        return errors

    if tokens[1] != "restrictions":
        errors.append({record_type: f"Invalid file header tag {tokens[1]}"})

    return errors


def validate_licence_product_line(record):
    errors = []
    tokens = record.split("\\")
    record_type = tokens[1]
    controlled_by = tokens[8]

    if len(tokens) != LICENCE_LINE_FIELDS_LEN:
        errors.append({record_type: f"{record_type} doesn't contain all necessary values"})
        return errors

    if tokens[1] != "line":
        errors.append({record_type: f"Invalid file header tag {tokens[1]}"})

    if tokens[7] == "":
        errors.append({record_type: "Product description cannot be empty"})

    if controlled_by not in CONTROLLED_BY_VALUES:
        errors.append({record_type: "Invalid controlled by value"})

    if len(tokens[10]) != 3:
        errors.append({record_type: "Quantity unit field should be of 3 characters wide"})

    return errors


def validate_end_line(record):
    errors = []
    tokens = record.split("\\")
    record_type = tokens[1]

    if len(tokens) != 4:
        errors.append({record_type: f"{record_type} doesn't contain all necessary values"})
        return errors

    if tokens[1] != "end":
        errors.append({record_type: f"Invalid file header tag {tokens[1]}"})

    return errors


def validate_file_trailer(record):
    errors = []
    tokens = record.split("\\")
    record_type = tokens[1]

    if len(tokens) != FILE_TRAILER_FIELDS_LEN:
        errors.append({record_type: f"{record_type} doesn't contain all necessary values"})
        return errors

    if tokens[1] != "fileTrailer":
        errors.append({record_type: f"Invalid file header tag {tokens[1]}"})

    return errors


def validate_edifact_file(file_data):
    """
    Validates the content as per the DES236 specification

    Validates each line and returns the list of discrepencies
    """
    file_lines = [line for line in file_data.split("\n") if line]

    errors = []
    data_identifier = ""
    for line in file_lines[:]:
        line_errors = list()
        tokens = line.split("\\")
        record_type = tokens[1]

        if record_type == "fileHeader":
            data_identifier = tokens[4]
            line_errors = validate_file_header(line)
        elif record_type == "licence":
            line_errors = validate_licence_transaction_header(data_identifier, line)
        elif record_type == "trader":
            line_errors = validate_permitted_trader(line)
        elif record_type == "country":
            line_errors = validate_country(line)
        elif record_type == "foreignTrader":
            line_errors = validate_foreign_trader(line)
        elif record_type == "restrictions":
            line = validate_restrictions(line)
        elif record_type == "line":
            line_errors = validate_licence_product_line(line)
        elif record_type == "end":
            line_errors = validate_end_line(line)
        elif record_type == "fileTrailer":
            line_errors = validate_file_trailer(line)
        else:
            line_errors.append(f"Invalid record type {record_type}")

        errors.extend(line_errors)

    return errors
