import logging
import os
from logging.handlers import RotatingFileHandler
from PyQt5.QtWidgets import QMessageBox

class Logger:
    def __init__(self, log_file='app.log', max_size=5*1024*1024, backup_count=3):
        self.logger = logging.getLogger('ChatbotApp')
        self.logger.setLevel(logging.WARNING)

        # Create logs directory if it doesn't exist
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # File handler with rotation
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, log_file),
            maxBytes=max_size,
            backupCount=backup_count
        )
        file_handler.setLevel(logging.DEBUG)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Create formatters and add them to handlers
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)

        # Add handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message, exc_info=False):
        self.logger.error(message, exc_info=exc_info)

    def critical(self, message, exc_info=False):
        self.logger.critical(message, exc_info=exc_info)

    def exception(self, message):
        self.logger.exception(message)

    def log_and_show(self, level, message, show_message_box=True):
        """Log a message and optionally show it in a QMessageBox."""
        getattr(self.logger, level)(message)
        if show_message_box:
            QMessageBox.warning(None, "Warning", message)

# Create a global logger instance
app_logger = Logger()

# Usage example:
# from logger import app_logger
# app_logger.info("Application started")
# app_logger.error("An error occurred")
# app_logger.log_and_show("warning", "This is a warning message", True)
