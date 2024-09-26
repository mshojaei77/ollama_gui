# model_handler.py
import logging
import json
from PyQt5.QtWidgets import QMessageBox
from langchain_community.chat_models import ChatOllama
from utility import Utility
import sys
import subprocess
from handlers.settings_handler import SETTINGS, save_settings
from logger import app_logger

class ModelHandler:
    def __init__(self, app):
        self.app = app
        self.load_models_from_json()
        self.app.ui.model_selector_lineEdit.setVisible(False)  # Hide lineEdit initially
        self.set_current_model_from_settings()  # Add this line

    def load_models_from_json(self):
        try:
            with open('data\models.json', 'r') as f:
                models = json.load(f)
            models.append("MANUAL ENTRY")
            self.app.ui.model_selector_comboBox.clear()
            self.app.ui.model_selector_comboBox.addItems(models)
            self.app.ui.model_selector_comboBox.currentTextChanged.connect(self._on_model_changed)
        except Exception as e:
            app_logger.error(f"Error loading models from JSON: {str(e)}")
            self.app.ui.model_selector_comboBox.addItem("MANUAL ENTRY")

    def set_current_model_from_settings(self):
        current_model = SETTINGS['model']
        index = self.app.ui.model_selector_comboBox.findText(current_model)
        if index >= 0:
            self.app.ui.model_selector_comboBox.setCurrentIndex(index)
        else:
            self.app.ui.model_selector_comboBox.setCurrentText("MANUAL ENTRY")
            self.app.ui.model_selector_lineEdit.setText(current_model)
            self.app.ui.model_selector_lineEdit.setVisible(True)

    def _on_model_changed(self, text):
        self.app.ui.model_selector_lineEdit.setVisible(text == "MANUAL ENTRY")
        if text != "MANUAL ENTRY":
            SETTINGS['model'] = text
            save_settings(SETTINGS)
            self.change_model()

    def change_model(self):
        try:
            self._configure_llm()
            self._log_model_change()
        except Exception as e:
            self._handle_model_change_error(e)

    def _configure_llm(self):
        self.app.llm = ChatOllama(
            model=SETTINGS['model'],
            temperature=SETTINGS['temperature'],
            num_ctx=SETTINGS['num_ctx'],
            num_gpu=SETTINGS['num_gpu'],
            num_thread=SETTINGS['num_thread'],
            top_k=SETTINGS['top_k'],
            top_p=SETTINGS['top_p'],
            repeat_penalty=SETTINGS['repeat_penalty'],
            repeat_last_n=SETTINGS['repeat_last_n'],
            seed=SETTINGS['seed'],
            mirostat=SETTINGS['mirostat'],
            mirostat_tau=SETTINGS['mirostat_tau'],
            mirostat_eta=SETTINGS['mirostat_eta'],
            f16_kv=SETTINGS['f16_kv'],
            logits_all=SETTINGS['logits_all'],
            vocab_only=SETTINGS['vocab_only'],
            streaming=True,
            callbacks=[self.app.stream_handler],
        )

    def _log_model_change(self):
        message = f"The {SETTINGS['model']} model is loaded"
        self.app.ui_handler.add_system_message(message)
        app_logger.info(message)

    def _handle_model_change_error(self, error):
        error_message = str(error)
        app_logger.error(f"Failed to change model: {error_message}")
        if "404" in error_message:
            model_name = SETTINGS['model']
            reply = QMessageBox.question(self.app, "Model Not Found", 
                                         f"The model {model_name} is not found. Do you want to pull it?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                self.pull_model(model_name)
        else:
            QMessageBox.critical(self.app, "Error", f"Failed to change model: {error_message}")
        self.app.llm = None

    def list_models(self):
        try:
            ollama_path = Utility.find_ollama_executable()
            if not ollama_path:
                self._show_ollama_not_found_error()
                return
            self._open_terminal_with_ollama_list(ollama_path)
        except Exception as e:
            self._handle_list_models_error(e)

    def _show_ollama_not_found_error(self):
        error_message = "Ollama executable not found. Please ensure Ollama is installed and added to your system's PATH."
        app_logger.error(error_message)
        QMessageBox.critical(self.app, "Error", error_message)

    def _open_terminal_with_ollama_list(self, ollama_path):
        if sys.platform.startswith('win'):
            powershell_command = f'Start-Process powershell -ArgumentList "-NoExit", "-Command", "& \'{ollama_path}\' list"'
            subprocess.Popen(['powershell', '-Command', powershell_command], creationflags=subprocess.CREATE_NEW_CONSOLE)
        elif sys.platform.startswith('darwin'):
            subprocess.Popen(['open', '-a', 'Terminal', ollama_path, 'list'])
        else:
            subprocess.Popen(['x-terminal-emulator', '-e', f'{ollama_path} list'])

    def _handle_list_models_error(self, error):
        error_message = f"An error occurred while trying to list models: {str(error)}\nPlease check your Ollama installation and try again."
        app_logger.error(error_message)
        QMessageBox.critical(self.app, "Error", error_message)

    def change_model_dialog(self):
        try:
            selected_model = self._get_selected_model()
            if selected_model:
                SETTINGS['model'] = selected_model
                self.change_model()
                save_settings(SETTINGS)
            else:
                self._show_model_selection_warning()
        except Exception as e:
            self._handle_model_change_error(e)

    def _get_selected_model(self):
        if self.app.ui.model_selector_comboBox.currentText() == "MANUAL ENTRY":
            return self.app.ui.model_selector_lineEdit.text()
        else:
            return self.app.ui.model_selector_comboBox.currentText()

    def _show_model_selection_warning(self):
        warning_message = "Please select or enter a model name."
        app_logger.warning(warning_message)
        QMessageBox.warning(self.app, "Warning", warning_message)

    def pull_model(self, model_name):
        try:
            ollama_path = Utility.find_ollama_executable()
            if not ollama_path:
                self._show_ollama_not_found_error()
                return
            if sys.platform.startswith('win'):
                powershell_command = f'Start-Process powershell -ArgumentList "-NoExit", "-Command", "& \'{ollama_path}\' pull {model_name}"'
                subprocess.Popen(['powershell', '-Command', powershell_command], creationflags=subprocess.CREATE_NEW_CONSOLE)
            elif sys.platform.startswith('darwin'):
                subprocess.Popen(['open', '-a', 'Terminal', ollama_path, 'pull', model_name])
            else:
                subprocess.Popen(['x-terminal-emulator', '-e', f'{ollama_path} pull {model_name}'])
        except Exception as e:
            error_message = f"Error pulling model: {str(e)}"
            app_logger.error(error_message)
            QMessageBox.critical(self.app, "Error", error_message)