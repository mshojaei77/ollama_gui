# settings_handler.py
import logging
from PyQt5.QtWidgets import QMessageBox
import os
import json
import appdirs
from logger import app_logger  # Import the custom logger
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt

# Global variables for settings
CONFIG_DIR = appdirs.user_config_dir("OllamaChatbot")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# ... existing code ...

# Default settings
DEFAULT_SETTINGS = {
    "model": "llama3.2:1b",  # Default language model to use
    "temperature": 0.8,  # Controls randomness in output generation
    "num_ctx": 2048,  # Context window size
    "top_k": 40,  # Limits vocabulary to top K most likely tokens
    "top_p": 0.9,  # Nucleus sampling threshold
    "repeat_penalty": 1.1,  # Penalty for repeating tokens
    "repeat_last_n": 64,  # Number of tokens to consider for repeat penalty
    "seed": -1,  # Random seed for reproducibility (-1 means random)
    "f16_kv": False,  # Use half-precision for key/value cache
    "logits_all": False,  # Return logits for all tokens
    "vocab_only": False,  # Only return vocabulary
    "font_size": 12,  # UI font size
    "theme": "Light",  # UI theme (Light or Dark)
    "max_tokens": 2048,  # Maximum number of tokens to generate
    "stop_sequences": "",  # Sequences to stop generation
    "presence_penalty": 0.0,  # Penalty for token presence in context
    "frequency_penalty": 0.0,  # Penalty for token frequency in context
    "memory_type": "ConversationBufferMemory",  # Type of conversation memory to use
    "memory_k": 5  # Number of recent conversations to remember
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
            self.add_system_message(f"Theme changed to {theme} mode. Your eyes will thank you!")
        except Exception as e:
            app_logger.error(f"Error loading stylesheet: {str(e)}")
            self.add_system_message("Oops! We couldn't change the theme. Don't worry, the app will still work fine!")

    def apply_settings(self):
        """Apply the current settings to the application."""
        try:
            self.app.setStyleSheet(f"font-size: {SETTINGS['font_size']}px;")
            self.load_stylesheet()
            self.set_window_frame_color()
            if hasattr(self.app, 'model_handler'):
                self.app.model_handler.change_model()
            if hasattr(self.app, 'memory_handler'):
                self.app.memory_handler.update_memory_settings()
            self.add_system_message(f"Great news! We're now using the {SETTINGS['model']} model. It's like upgrading your brain!")
            self.add_system_message(f"Font size is set to {SETTINGS['font_size']}. If it's too small, you can change it in the settings!")
            app_logger.info("Settings applied successfully")
            self.add_system_message("All your settings have been applied successfully. Happy chatting!")
        except Exception as e:
            app_logger.error(f"Error applying settings: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to apply settings: {str(e)}")
            self.add_system_message("We hit a small bump while applying your settings. But don't worry, we're still here for you!")

    def add_system_message(self, message):
        """Add a system message if ui_handler is available, otherwise log it."""
        if hasattr(self.app, 'ui_handler'):
            self.app.ui_handler.add_system_message(message)
        else:
            app_logger.info(f"System message (not displayed): {message}")

    def set_window_frame_color(self):
        """Set the window frame color based on the current theme."""
        if SETTINGS['theme'] == 'Dark':
            self.app.setStyleSheet(self.app.styleSheet() + """
                QMainWindow {
                    border: 1px solid #45474a;
                }
                QMainWindow::title {
                    background-color: #2d2d2d;
                    color: white;
                }
            """)
            # Set the window frame to dark
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(45, 45, 45))
            palette.setColor(QPalette.WindowText, Qt.white)
            self.app.setPalette(palette)
        else:
            # Reset to default light theme
            self.app.setStyleSheet(self.app.styleSheet().replace("""
                QMainWindow {
                    border: 1px solid #45474a;
                }
                QMainWindow::title {
                    background-color: #2d2d2d;
                    color: white;
                }
            """, ""))
            self.app.setPalette(self.app.style().standardPalette())
        
        app_logger.info(f"Window frame color set to {SETTINGS['theme']} mode")
        self.add_system_message(f"Window frame color changed to match {SETTINGS['theme']} mode. Looking good!")

    def toggle_dark_mode(self):
        """Toggle between light and dark mode."""
        try:
            SETTINGS['theme'] = 'Light' if SETTINGS['theme'] == 'Dark' else 'Dark'
            save_settings(SETTINGS)
            self.apply_settings()
            app_logger.info(f"Toggled to {SETTINGS['theme']} mode")
            self.add_system_message(f"Switched to {SETTINGS['theme']} mode. How's the view?")
        except Exception as e:
            app_logger.error(f"Error toggling dark mode: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to toggle dark mode: {str(e)}")
            self.add_system_message("We couldn't switch the theme right now. But don't let that dim your spirits!")

    def open_settings(self):
        """Open the settings dialog."""
        try:
            from widgets.settings import SettingsDialog
            settings_dialog = SettingsDialog(self.app)
            if settings_dialog.exec_():
                self.apply_settings()
            app_logger.info("Settings dialog opened and closed")
            self.add_system_message("Settings updated! Feel free to tweak them anytime to make the app work best for you.")
        except Exception as e:
            app_logger.error(f"Error opening settings: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to open settings: {str(e)}")
            self.add_system_message("We couldn't open the settings right now. But don't worry, your current settings are still working!")
            if "'range' is an unknown keyword argument" in str(e):
                app_logger.error("This error might be caused by an incompatibility with the QDoubleSpinBox widget. Please check the SettingsDialog initialization.")