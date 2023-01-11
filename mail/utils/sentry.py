import sentry_sdk


def log_to_sentry(message, extra=None, level="info"):
    extra = extra or {}
    with sentry_sdk.push_scope() as scope:
        for key, value in extra.items():
            scope.set_extra(key, value)
        sentry_sdk.capture_message(message, level=level)
