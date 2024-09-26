import logging
import json
import os
import appdirs
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QTabWidget, QWidget, QFormLayout
)
from PyQt5.QtCore import Qt
from handlers.settings_handler import SETTINGS
from logger import app_logger  # Import the logger

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        try:
            self.setWindowTitle("Settings")
            self.resize(600, 400)
            self.layout = QVBoxLayout(self)

            # Create tabs
            self.tabs = QTabWidget()
            self.layout.addWidget(self.tabs)

            # Initialize tabs
            self.initialize_model_tab()
            self.initialize_ui_tab()
            self.initialize_advanced_tab()
            self.initialize_memory_tab()

            # $ Save Button
            self.save_button = QPushButton("Save")
            self.save_button.clicked.connect(self.accept)
            self.layout.addWidget(self.save_button)

            self.load_settings_to_ui()

        except Exception as e:
            app_logger.error(f"Error in SettingsDialog initialization: {str(e)}")

    def initialize_model_tab(self):
        # $ Model Settings Tab
        self.model_tab = QWidget()
        self.model_layout = QFormLayout(self.model_tab)
        self.tabs.addTab(self.model_tab, "Model Settings")

        # $ Model Settings UI Elements
        self.temperature = QDoubleSpinBox(range=(0, 2), singleStep=0.1, value=0.8)
        self.num_ctx = QSpinBox(range=(1, 8192), value=2048)
        self.num_gpu = QSpinBox(range=(0, 8), value=1)
        self.num_thread = QSpinBox(range=(1, 32), value=4)
        self.top_k = QSpinBox(range=(1, 100), value=40)
        self.top_p = QDoubleSpinBox(range=(0, 1), singleStep=0.05, value=0.9)
        self.repeat_penalty = QDoubleSpinBox(range=(0, 2), singleStep=0.1, value=1.1)
        self.repeat_last_n = QSpinBox(range=(0, 2048), value=64)
        self.seed = QSpinBox(range=(-1, 2147483647), value=-1)
        self.mirostat = QComboBox()
        self.mirostat.addItems(["0", "1", "2"])
        self.mirostat_tau = QDoubleSpinBox(range=(0, 10), singleStep=0.1, value=5.0)
        self.mirostat_eta = QDoubleSpinBox(range=(0, 1), singleStep=0.01, value=0.1)
        self.f16_kv = QCheckBox()
        self.logits_all = QCheckBox()
        self.vocab_only = QCheckBox()

        # $ System Prompt
        self.system_prompt = QTextEdit()
        self.system_prompt.setPlaceholderText("Enter system prompt here...")

        # Add widgets to layout
        model_settings = [
            ("Temperature:", self.temperature),
            ("Context Length:", self.num_ctx),
            ("Number of GPUs:", self.num_gpu),
            ("Number of Threads:", self.num_thread),
            ("Top K:", self.top_k),
            ("Top P:", self.top_p),
            ("Repeat Penalty:", self.repeat_penalty),
            ("Repeat Last N:", self.repeat_last_n),
            ("Seed:", self.seed),
            ("Mirostat:", self.mirostat),
            ("Mirostat Tau:", self.mirostat_tau),
            ("Mirostat Eta:", self.mirostat_eta),
            ("Use F16 KV:", self.f16_kv),
            ("Logits All:", self.logits_all),
            ("Vocab Only:", self.vocab_only),
            ("System Prompt:", self.system_prompt)
        ]

        for label, widget in model_settings:
            self.model_layout.addRow(label, widget)

    def initialize_ui_tab(self):
        # $ UI Settings Tab
        self.ui_tab = QWidget()
        self.ui_layout = QFormLayout(self.ui_tab)
        self.tabs.addTab(self.ui_tab, "UI Settings")

        # $ UI Settings Elements
        self.font_size = QSpinBox(range=(8, 24), value=12)
        self.theme = QComboBox()
        self.theme.addItems(["Light", "Dark", "System"])

        self.ui_layout.addRow("Font Size:", self.font_size)
        self.ui_layout.addRow("Theme:", self.theme)

    def initialize_advanced_tab(self):
        # $ Advanced Settings Tab
        self.advanced_tab = QWidget()
        self.advanced_layout = QFormLayout(self.advanced_tab)
        self.tabs.addTab(self.advanced_tab, "Advanced Settings")

        # $ Advanced Settings Elements
        self.max_tokens = QSpinBox(range=(1, 8192), value=2048)
        self.stop_sequences = QLineEdit()
        self.stop_sequences.setPlaceholderText("Enter stop sequences separated by comma")
        self.presence_penalty = QDoubleSpinBox(range=(-2.0, 2.0), singleStep=0.1, value=0.0)
        self.frequency_penalty = QDoubleSpinBox(range=(-2.0, 2.0), singleStep=0.1, value=0.0)

        advanced_settings = [
            ("Max Tokens:", self.max_tokens),
            ("Stop Sequences:", self.stop_sequences),
            ("Presence Penalty:", self.presence_penalty),
            ("Frequency Penalty:", self.frequency_penalty)
        ]

        for label, widget in advanced_settings:
            self.advanced_layout.addRow(label, widget)

    def initialize_memory_tab(self):
        # $ Memory Settings Tab
        self.memory_tab = QWidget()
        self.memory_layout = QFormLayout(self.memory_tab)
        self.tabs.addTab(self.memory_tab, "Memory Settings")

        # $ Memory Settings Elements
        self.memory_type = QComboBox()
        self.memory_type.addItems(["ConversationBufferMemory", "ConversationBufferWindowMemory", "ConversationSummaryMemory"])
        self.memory_k = QSpinBox(range=(1, 100), value=5)

        self.memory_layout.addRow("Memory Type:", self.memory_type)
        self.memory_layout.addRow("Memory K:", self.memory_k)

    def load_settings_to_ui(self):
        try:
            for key, value in SETTINGS.items():
                if hasattr(self, key):
                    widget = getattr(self, key)
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
                if hasattr(self, key):
                    widget = getattr(self, key)
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
            
            self.parent.update_settings(new_settings)
            app_logger.info("Settings updated successfully")
            super().accept()
        except Exception as e:
            app_logger.error(f"Error updating settings: {str(e)}")

