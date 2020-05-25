import logging


def lite_logging(logging_data: dict, keys_to_exclude: list = None):
    if keys_to_exclude is None:
        keys_to_exclude = []
    data = {"message": "liteolog hmrc"}
    for key in logging_data:
        if len(keys_to_exclude) == 0 or key not in keys_to_exclude:
            value = logging_data[key]
            if len(value) > 100:
                value = value[0:100]
            data[key] = value
    logging.info(data)


def lite_log(logger: logging.Logger, log_level: int, logging_msg: str):
    data = {"message": "liteolog hmrc"}
    msg = logging_msg
    if len(logging_msg) > 500:
        msg = logging_msg[0:500]
    data["logging_msg"] = msg
    logger_funcs = {
        logging.DEBUG: log_debug,
        logging.INFO: log_info,
        logging.WARN: log_warn,
        logging.ERROR: log_error,
    }
    _func = logger_funcs.get(
        log_level, lambda: "{} log level is not recognized".format(log_level)
    )
    _func(logger, data)


def lite_logging_decorator(func):
    """A decorator produces logging data before and after an annotated function is called.
       *Note*: this is only for functions do not return any values
     """

    def wrapper(*args, **kwargs):
        lite_logging(
            {
                "function_name": func.__name__,
                "function_qualified_name": func.__qualname__,
                "function_position": "start",
            }
        )
        try:
            func(*args, **kwargs)
            lite_logging(
                {
                    "function_end": func.__name__,
                    "function_qualified_name": func.__qualname__,
                    "function_position": "end",
                }
            )
        except Exception as e:
            lite_logging(
                {
                    "function_end": func.__name__,
                    "function_qualified_name": func.__qualname__,
                    "function_position": "exception thrown",
                    "exception": str(e),
                }
            )
            raise e

    return wrapper


# todo create a new logging decorator which can annotate these functions return values, though not sure we need it


def log_debug(logger, msg):
    return logger.debug(msg)


def log_info(logger, msg):
    return logger.info(msg)


def log_warn(logger, msg):
    return logger.warn(msg)


def log_error(logger, msg):
    return logger.error(msg)
