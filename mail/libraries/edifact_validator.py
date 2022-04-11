import re

from mail.enums import LITE_HMRC_LICENCE_TYPE_MAPPING, LicenceActionEnum

FILE_HEADER_FIELDS_LEN = 8
LICENCE_TRANSACTION_HEADER_FIELDS_LEN = 9
PERMITTED_TRADER_HEADER_FIELDS_LEN = 13
PERMITTED_TRADER_NAME_MAX_LEN = 80
PERMITTED_TRADER_ADDR_LINE_MAX_LEN = 35
COUNTRY_FIELDS_LEN = 5
FOREIGN_TRADER_FIELDS_LEN = 10
FOREIGN_TRADER_NAME_MAX_LEN = 80
FOREIGN_TRADER_NUM_ADDR_LINES = 5
FOREIGN_TRADER_ADDR_LINE_MAX_LEN = 35
FOREIGN_TRADER_POSTCODE_MAX_LEN = 8
FOREIGN_TRADER_COUNTRY_MAX_LEN = 2
LICENCE_LINE_FIELDS_LEN = 19
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


def is_postcode_valid(value):
    """
    Postcode validator for UK based postcodes only
    Reused from lite-api (validate_postcode() in api/addresses/serializers.py)
    """
    outcode_pattern = "[A-PR-UWYZ]([0-9]{1,2}|([A-HIK-Y][0-9](|[0-9]|[ABEHMNPRVWXY]))|[0-9][A-HJKSTUW])"
    incode_pattern = "[0-9][ABD-HJLNP-UW-Z]{2}"
    postcode_regex = re.compile(r"^(GIR 0AA|%s %s)$" % (outcode_pattern, incode_pattern))
    space_regex = re.compile(r" *(%s)$" % incode_pattern)

    postcode = value.upper().strip()
    # Put a single space before the incode (second part).
    postcode = space_regex.sub(r" \1", postcode)

    if not postcode_regex.search(postcode):
        return False

    return True


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

    if len(rpa_trader_id) < 12 or len(rpa_trader_id) > 15:
        errors.append({record_type: "RPA Trader Id must be of atleast 12 chars and max 15 chars wide"})

    if int(tokens[5]) < int(tokens[4]):
        errors.append({record_type: "Invalid start and end dates for the licence"})

    organisation_name = tokens[6]
    if len(organisation_name) > PERMITTED_TRADER_NAME_MAX_LEN:
        errors.append({record_type: f"Organisation name cannot exceed {PERMITTED_TRADER_NAME_MAX_LEN} chars"})

    for i in range(5):
        if len(tokens[7 + i]) > PERMITTED_TRADER_ADDR_LINE_MAX_LEN:
            errors.append({record_type: f"Address line cannot exceed {PERMITTED_TRADER_ADDR_LINE_MAX_LEN} chars"})

    if not is_postcode_valid(tokens[12]):
        errors.append({record_type: f"Invalid postcode found {tokens[12]}"})

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

    name = tokens[2]
    if len(name) > FOREIGN_TRADER_NAME_MAX_LEN:
        errors.append({record_type: f"Foreign trader name ({name}) cannot exceed {FOREIGN_TRADER_NAME_MAX_LEN} chars"})

    for index, line in enumerate(tokens[3:8], start=1):
        if len(line) > FOREIGN_TRADER_ADDR_LINE_MAX_LEN:
            errors.append(
                {record_type: f"Address line_{index} ({line}) trader exceeds {FOREIGN_TRADER_ADDR_LINE_MAX_LEN} chars"}
            )

    postcode = tokens[8]
    country = tokens[9]
    if len(postcode) > FOREIGN_TRADER_POSTCODE_MAX_LEN:
        errors.append(
            {record_type: f"Foreign trader postcode ({postcode}) exceeds {FOREIGN_TRADER_POSTCODE_MAX_LEN} chars"}
        )

    if len(country) > FOREIGN_TRADER_COUNTRY_MAX_LEN:
        errors.append(
            {record_type: f"Foreign trader country code ({country}) exceeds {FOREIGN_TRADER_COUNTRY_MAX_LEN} chars"}
        )

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
