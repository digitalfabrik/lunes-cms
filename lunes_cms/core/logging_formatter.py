from __future__ import annotations

import logging
from logging import LogRecord


class ColorFormatter(logging.Formatter):
    """
    Logging Formatter to add colors
    """

    #: The bash color codes for the different logging levels
    COLORS = {
        logging.DEBUG: 36,  # cyan
        logging.INFO: 34,  # blue
        logging.WARNING: 33,  # yellow
        logging.ERROR: 31,  # red
        logging.CRITICAL: 31,  # red
    }

    def format(self, record: LogRecord) -> str:
        """
        Format the specified record as colored text (see :meth:`python:logging.Formatter.format`).

        :param record: The log record
        :type record: ~logging.LogRecord

        :return: The formatted logging message
        :rtype: str
        """
        # Define color escape sequence
        color = f"\x1b[0;{self.COLORS.get(record.levelno)}m"
        # Make level name bold
        # ``_fmt`` may be None if the formatter was constructed without an
        # explicit format string; fall back to the empty string in that case.
        fmt = (self._fmt or "").replace("{levelname}", "\x1b[1m{levelname}" + color)
        # Make entire line colored
        # pylint: disable=protected-access
        self._style._fmt = color + fmt + "\x1b[0m"
        return super().format(record)
