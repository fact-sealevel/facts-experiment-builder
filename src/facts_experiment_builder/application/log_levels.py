"""Custom log level shared by application code and the CLI log handler."""

import logging

SUCCESS = 25  # between INFO (20) and WARNING (30)
logging.addLevelName(SUCCESS, "SUCCESS")
