class RetrievedEmailStatusEnum:
    VALID = "valid"
    INVALID = "invalid"

    choices = [
        (VALID, "Valid"),
        (INVALID, "Invalid"),
    ]


class HmrcMailStatusEnum:
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REPLIED = "replied"
    RETRY = "retry"
    FAILED = "failed"

    choices = [
        (ACCEPTED, "Accepted"),
        (REJECTED, "Rejected"),
        (REPLIED, "Replied"),
        (RETRY, "Retry"),
        (FAILED, "Failed"),
    ]
