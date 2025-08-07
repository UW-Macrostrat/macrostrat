import logging

disable_loggers = ["macrostrat.database.utils"]


def pytest_configure():
    # Quiet verbose logging
    for logger_name in disable_loggers:
        logger = logging.getLogger(logger_name)
        logger.disabled = True
