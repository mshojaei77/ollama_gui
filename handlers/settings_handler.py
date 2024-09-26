# settings_handler.py
import logging
from PyQt5.QtWidgets import QMessageBox
import os
import json
import appdirs
from logger import app_logger  # Import the custom logger

# Global variables for settings
CONFIG_DIR = appdirs.user_config_dir("OllamaChatbot")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# Default settings
DEFAULT_SETTINGS = {
    "model": "llama3.2:1b",
    "temperature": 0.8,
    "num_ctx": 2048,
    "num_gpu": 1,
    "num_thread": 4,
    "top_k": 40,
    "top_p": 0.9,
    "repeat_penalty": 1.1,
    "repeat_last_n": 64,
    "seed": -1,
    "mirostat": 0,
    "mirostat_tau": 5.0,
    "mirostat_eta": 0.1,
    "f16_kv": False,
    "logits_all": False,
    "vocab_only": False,
    "font_size": 12,
    "theme": "Light",
    "max_tokens": 2048,
    "stop_sequences": "",
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "memory_type": "ConversationBufferMemory",
    "memory_k": 5
}

def load_settings():
    """Load settings from the config file or return default settings."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return DEFAULT_SETTINGS.copy()
    except Exception as e:
        app_logger.error(f"Error loading settings: {str(e)}")
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Save settings to the config file."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
        app_logger.info("Settings saved successfully")
    except Exception as e:
        app_logger.error(f"Error saving settings: {str(e)}")

# Global settings variable
SETTINGS = load_settings()

class SettingsHandler:
    def __init__(self, app):
        self.app = app

    def load_stylesheet(self):
        """Load the appropriate stylesheet based on the current theme."""
        try:
            theme = 'dark' if SETTINGS['theme'] == 'Dark' else 'light'
            with open(f'styles/{theme}.qss', 'r') as f:
                stylesheet = f.read()
            self.app.setStyleSheet(stylesheet)
            app_logger.info(f"Loaded {theme} stylesheet")
        except Exception as e:
            app_logger.error(f"Error loading stylesheet: {str(e)}")

    def apply_settings(self):
        """Apply the current settings to the application."""
        try:
            # $ UI Element: Set font size
            self.app.setStyleSheet(f"font-size: {SETTINGS['font_size']}px;")
            self.load_stylesheet()
            self.app.model_handler.change_model()
            self.app.memory_handler.update_memory_settings()
            # $ UI Element: Add system message
            self.app.ui_handler.add_system_message(f"Using model: {SETTINGS['model']}")
            app_logger.info("Settings applied successfully")
        except Exception as e:
            app_logger.error(f"Error applying settings: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to apply settings: {str(e)}")

    def toggle_dark_mode(self):
        """Toggle between light and dark mode."""
        try:
            SETTINGS['theme'] = 'Light' if SETTINGS['theme'] == 'Dark' else 'Dark'
            save_settings(SETTINGS)
            self.apply_settings()
            app_logger.info(f"Toggled to {SETTINGS['theme']} mode")
        except Exception as e:
            app_logger.error(f"Error toggling dark mode: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to toggle dark mode: {str(e)}")

    def open_settings(self):
        """Open the settings dialog."""
        try:
            from widgets.settings import SettingsDialog
            settings_dialog = SettingsDialog(self.app)
            if settings_dialog.exec_():
                self.apply_settings()
            app_logger.info("Settings dialog opened and closed")
        except Exception as e:
            app_logger.error(f"Error opening settings: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to open settings: {str(e)}")