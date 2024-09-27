import logging
import json
import os
import appdirs
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import Qt
from handlers.settings_handler import SETTINGS, save_settings
from logger import app_logger  # Import the logger
from views.settings_ui import Ui_SettingsDialog  # Import the Ui_SettingsDialog class
from PyQt5.QtWidgets import QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QTextEdit, QLineEdit

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.ui = Ui_SettingsDialog()
        self.ui.setupUi(self)
        self.initUI()

    def initUI(self):
        try:
            self.setWindowTitle("Settings")
            self.resize(900, 500)

            # Connect the save button
            self.ui.save_button.clicked.connect(self.accept)

            self.load_settings_to_ui()

        except Exception as e:
            app_logger.error(f"Error in SettingsDialog initialization: {str(e)}")

    def load_settings_to_ui(self):
        try:
            for key, value in SETTINGS.items():
                if hasattr(self.ui, key):
                    widget = getattr(self.ui, key)
                    if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                        widget.setValue(value)
                    elif isinstance(widget, QComboBox):
                        widget.setCurrentText(str(value))
                    elif isinstance(widget, QCheckBox):
                        widget.setChecked(value)
                    elif isinstance(widget, QTextEdit):
                        widget.setPlainText(value)
                    elif isinstance(widget, QLineEdit):
                        widget.setText(value)
            app_logger.info("Settings loaded successfully to UI")
        except Exception as e:
            app_logger.error(f"Error loading settings to UI: {str(e)}")

    def accept(self):
        try:
            new_settings = {}
            for key in SETTINGS.keys():
                if hasattr(self.ui, key):
                    widget = getattr(self.ui, key)
                    if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                        new_settings[key] = widget.value()
                    elif isinstance(widget, QComboBox):
                        new_settings[key] = widget.currentText()
                    elif isinstance(widget, QCheckBox):
                        new_settings[key] = widget.isChecked()
                    elif isinstance(widget, QTextEdit):
                        new_settings[key] = widget.toPlainText()
                    elif isinstance(widget, QLineEdit):
                        new_settings[key] = widget.text()
            
            # Update the global SETTINGS
            SETTINGS.update(new_settings)
            # Save the updated settings
            save_settings(SETTINGS)
            # Apply the new settings
            self.parent.settings_handler.apply_settings()
            app_logger.info("Settings updated and applied successfully")
            super().accept()
        except Exception as e:
            app_logger.error(f"Error updating settings: {str(e)}")