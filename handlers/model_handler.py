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
        self.app.ui_handler.add_system_message("Welcome! I'm ready to chat using the default model. You can change the model anytime from the dropdown menu.")

    def load_models_from_json(self):
        try:
            with open('data\\models.json', 'r') as f:
                models = json.load(f)
            models.append("MANUAL ENTRY")
            self.app.ui.model_selector_comboBox.clear()
            self.app.ui.model_selector_comboBox.addItems(models)
            self.app.ui.model_selector_comboBox.currentTextChanged.connect(self._on_model_changed)
            self.app.ui_handler.add_system_message("Available models have been loaded. You can select one from the dropdown menu.")
        except Exception as e:
            app_logger.error(f"Error loading models from JSON: {str(e)}")
            self.app.ui.model_selector_comboBox.addItem("MANUAL ENTRY")
            self.app.ui_handler.add_system_message("Oops! I couldn't load the list of models. You can still enter a model name manually.")

    def set_current_model_from_settings(self):
        current_model = SETTINGS['model']
        index = self.app.ui.model_selector_comboBox.findText(current_model)
        if index >= 0:
            self.app.ui.model_selector_comboBox.setCurrentIndex(index)
            self.app.ui_handler.add_system_message(f"I've set the current model to {current_model}. You're all set to start chatting!")
        else:
            self.app.ui.model_selector_comboBox.setCurrentText("MANUAL ENTRY")
            self.app.ui.model_selector_lineEdit.setText(current_model)
            self.app.ui.model_selector_lineEdit.setVisible(True)
            self.app.ui_handler.add_system_message(f"I've set the model to {current_model}. This is a custom entry. You can change it anytime.")

    def _on_model_changed(self, text):
        self.app.ui.model_selector_lineEdit.setVisible(text == "MANUAL ENTRY")
        if text != "MANUAL ENTRY":
            SETTINGS['model'] = text
            save_settings(SETTINGS)
            self.change_model()
            self.app.ui_handler.add_system_message(f"You've selected the {text} model. I'm updating my settings now.")

    def change_model(self):
        try:
            self._configure_llm()
            self._log_model_change()
        except Exception as e:
            self._handle_model_change_error(e)

    def _configure_llm(self):
        try:
            self.app.llm = ChatOllama(
                model=SETTINGS['model'],
                temperature=SETTINGS['temperature'],
                num_ctx=SETTINGS['num_ctx'],
                top_k=SETTINGS['top_k'],
                top_p=SETTINGS['top_p'],
                repeat_penalty=SETTINGS['repeat_penalty'],
                repeat_last_n=SETTINGS['repeat_last_n'],
                seed=SETTINGS['seed'],
                f16_kv=SETTINGS['f16_kv'],
                logits_all=SETTINGS['logits_all'],
                vocab_only=SETTINGS['vocab_only'],
                streaming=True,
                callbacks=[self.app.chat_handler.stream_handler],  # Use chat_handler's stream_handler
            )
            self.app.ui_handler.add_system_message("Great! I've updated my settings with the new model. We're ready to chat!")
        except Exception as e:
            app_logger.error(f"Error configuring LLM: {str(e)}")
            self.app.llm = None
            self.app.ui_handler.add_system_message("Oops! I had trouble setting up the new model. Let's try again or choose a different one.")
            raise RuntimeError(f"Failed to configure LLM: {str(e)}")

    def _log_model_change(self):
        message = f"The {SETTINGS['model']} model is loaded"
        self.app.ui_handler.add_system_message(message)
        app_logger.info(message)

    def _handle_model_change_error(self, error):
        error_message = str(error)
        app_logger.error(f"Failed to change model: {error_message}")
        if "404" in error_message:
            model_name = SETTINGS['model']
            self.app.ui_handler.add_system_message(f"Hmm, I couldn't find the {model_name} model. Would you like me to download it for you?")
            reply = QMessageBox.question(self.app, "Model Not Found", 
                                         f"The model {model_name} is not found. Do you want to pull it?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                self.pull_model(model_name)
            else:
                self.app.ui_handler.add_system_message("No problem! You can choose a different model or try again later.")
        else:
            QMessageBox.critical(self.app, "Error", f"Failed to change model: {error_message}")
            self.app.ui_handler.add_system_message("I'm sorry, but I encountered an error while changing the model. Let's try a different one!")
        self.app.llm = None

    def list_models(self):
        try:
            ollama_path = Utility.find_ollama_executable()
            if not ollama_path:
                self._show_ollama_not_found_error()
                return
            self._open_terminal_with_ollama_list(ollama_path)
            self.app.ui_handler.add_system_message("I'm opening a new window to show you the list of available models. Take a look!")
        except Exception as e:
            self._handle_list_models_error(e)

    def _show_ollama_not_found_error(self):
        error_message = "Ollama executable not found. Please ensure Ollama is installed and added to your system's PATH."
        app_logger.error(error_message)
        QMessageBox.critical(self.app, "Error", error_message)
        self.app.ui_handler.add_system_message("Oops! I couldn't find Ollama on your computer. Make sure it's installed and set up correctly.")

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
        self.app.ui_handler.add_system_message("I'm having trouble showing you the list of models. Can you check if Ollama is running correctly?")

    def change_model_dialog(self):
        try:
            selected_model = self._get_selected_model()
            if selected_model:
                SETTINGS['model'] = selected_model
                self.change_model()
                save_settings(SETTINGS)
                self.app.ui_handler.add_system_message(f"Great choice! I'm now using the {selected_model} model. Let's start chatting!")
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
        self.app.ui_handler.add_system_message("Oops! You forgot to select a model. Please choose one from the dropdown or enter a name.")

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
            self.app.ui_handler.add_system_message(f"I'm downloading the {model_name} model for you. This might take a while, depending on your internet speed. I'll let you know when it's ready!")
        except Exception as e:
            error_message = f"Error pulling model: {str(e)}"
            app_logger.error(error_message)
            QMessageBox.critical(self.app, "Error", error_message)
            self.app.ui_handler.add_system_message(f"I'm sorry, but I couldn't download the {model_name} model. There might be a problem with your internet connection or Ollama setup.")