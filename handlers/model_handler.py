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
from handlers.get_trending_models import get_ollama_models

class ModelHandler:
    def __init__(self, app):
        self.app = app
        self.app.ui.model_selector_lineEdit.setVisible(True)   # Always show lineEdit
        self.setup_model_list_button()
        self.setup_model_load_button()
        self.set_current_model_from_settings(load_model=False)  # Don't load model automatically
        self.app.ui_handler.add_system_message("Welcome! Enter a model name and click 'Load Model' to start chatting.")

    def setup_model_list_button(self):
        # Use the existing button in the UI
        self.app.ui.model_list_button.setToolTip("Show list of popular models")
        self.app.ui.model_list_button.clicked.connect(self.show_popular_models)

    def setup_model_load_button(self):
        # Connect the model load button
        self.app.ui.model_load_button.clicked.connect(self.load_selected_model)
        self.app.ui.model_load_button.setToolTip("Load the selected model")

    def show_popular_models(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem
        
        try:
            get_ollama_models()
            # Load popular models from JSON
            with open('data\\models.json', 'r') as f:
                models = json.load(f)
                
            dialog = QDialog(self.app)
            dialog.setWindowTitle("Popular Models")
            layout = QVBoxLayout(dialog)
            
            list_widget = QListWidget()
            for model in models:
                item = QListWidgetItem(model)
                list_widget.addItem(item)
                
            list_widget.itemDoubleClicked.connect(lambda item: self.select_model_from_list(item.text(), dialog))
            layout.addWidget(list_widget)
            
            dialog.setLayout(layout)
            dialog.resize(300, 400)
            dialog.exec_()
        except Exception as e:
            app_logger.error(f"Error showing popular models: {str(e)}")
            self.app.ui_handler.add_system_message("Sorry, I couldn't load the list of popular models.")
            
    def select_model_from_list(self, model_name, dialog):
        self.app.ui.model_selector_lineEdit.setText(model_name)
        SETTINGS['model'] = model_name
        save_settings(SETTINGS)
        # Don't load model automatically
        self.app.ui_handler.add_system_message(f"You've selected the {model_name} model. Click 'Load Model' to start using it.")
        dialog.close()
        
    def load_models_from_json(self):
        # We're not loading models into comboBox anymore, but we'll keep this to maintain structure
        try:
            with open('data\\models.json', 'r') as f:
                json.load(f)  # Just validate the JSON
            self.app.ui_handler.add_system_message("You can enter a model name directly or click the list button to see popular options.")
        except Exception as e:
            app_logger.error(f"Error loading models from JSON: {str(e)}")
            self.app.ui_handler.add_system_message("Oops! I couldn't load the list of models. You can still enter a model name manually.")

    def set_current_model_from_settings(self, load_model=False):
        current_model = SETTINGS['model']
        self.app.ui.model_selector_lineEdit.setText(current_model)
        if load_model:
            self.change_model()
            self.app.ui_handler.add_system_message(f"I've set the model to {current_model}. You can change it anytime.")
        else:
            self.app.ui_handler.add_system_message(f"Model {current_model} is selected. Click 'Load Model' to start using it.")

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
            selected_model = self.app.ui.model_selector_lineEdit.text()
            if selected_model:
                SETTINGS['model'] = selected_model
                save_settings(SETTINGS)
                # Don't load model automatically
                self.app.ui_handler.add_system_message(f"Model changed to {selected_model}. Click 'Load Model' to start using it.")
            else:
                self._show_model_selection_warning()
        except Exception as e:
            self._handle_model_change_error(e)

    def _get_selected_model(self):
        return self.app.ui.model_selector_lineEdit.text()

    def _show_model_selection_warning(self):
        warning_message = "Please enter a model name."
        app_logger.warning(warning_message)
        QMessageBox.warning(self.app, "Warning", warning_message)
        self.app.ui_handler.add_system_message("Oops! You forgot to enter a model name. Please enter a model name.")

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

    def load_selected_model(self):
        try:
            selected_model = self.app.ui.model_selector_lineEdit.text()
            if not selected_model:
                self._show_model_selection_warning()
                return

            # Check if model exists locally
            try:
                ollama_path = Utility.find_ollama_executable()
                result = subprocess.run([ollama_path, 'show', selected_model], 
                                      capture_output=True, text=True, timeout=10)
                if "not found" in result.stderr:
                    raise RuntimeError(f"Model {selected_model} not found")
            except Exception as e:
                self._handle_missing_model(selected_model, e)
                return

            # If model exists, load it
            SETTINGS['model'] = selected_model
            save_settings(SETTINGS)
            self.change_model()
            self.app.ui_handler.add_system_message(f"Great! I'm now using the {selected_model} model. Let's start chatting!")

        except Exception as e:
            self._handle_model_change_error(e)

    def _handle_missing_model(self, model_name, error):
        app_logger.error(f"Model not found: {str(error)}")
        self.app.ui_handler.add_system_message(f"Hmm, I couldn't find the {model_name} model. Would you like me to download it for you?")
        
        reply = QMessageBox.question(self.app, "Model Not Found", 
                                   f"The model {model_name} is not installed. Do you want to download it?",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self.pull_model(model_name)
        else:
            self.app.ui_handler.add_system_message("No problem! You can choose a different model or try again later.")