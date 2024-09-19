import sys
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit,
    QPushButton, QHBoxLayout, QLabel, QScrollArea, QDesktopWidget,
    QMainWindow, QAction, QMenu, QDialog, QFormLayout, QDoubleSpinBox,
    QSpinBox, QComboBox, QCheckBox, QTabWidget, QGroupBox, QSlider,
    QFileDialog, QInputDialog, QMessageBox, QDialogButtonBox
)
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QThread
from langchain_community.chat_models import ChatOllama
from langchain.callbacks.base import BaseCallbackHandler
from langchain.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory
import json
import os
import logging
import shutil
import psutil
import platform
import GPUtil

# Set up logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

class StreamHandler(QObject, BaseCallbackHandler):
    new_token = pyqtSignal(str)

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.new_token.emit(token)

class ChatThread(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, llm, messages):
        super().__init__()
        self.llm = llm
        self.messages = messages
    
    def run(self):
        try:
            response = self.llm.invoke(self.messages)
            self.response_ready.emit(response.content)
        except Exception as e:
            logging.error(f"Error in ChatThread: {str(e)}")
            if "503" in str(e):
                self.error_occurred.emit("Error: Unable to connect to Ollama. Please ensure that any VPN or proxy is turned off.")
            else:
                self.error_occurred.emit(str(e))
            

class MessageWidget(QWidget):
    def __init__(self, message, is_user=True):
        super().__init__()
        layout = QHBoxLayout()
        text = QLabel(message)
        text.setWordWrap(True)
        text.setFont(QFont('Arial', 12))
        
        if is_user:
            layout.addStretch()
            text.setStyleSheet("background-color: #DCF8C6; border-radius: 10px; padding: 10px;")
        else:
            text.setStyleSheet("background-color: #FFFFFF; border-radius: 10px; padding: 10px;")
        
        layout.addWidget(text)
        
        if not is_user:
            layout.addStretch()
        
        self.setLayout(layout)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.layout = QVBoxLayout(self)

        # Create tabs
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # Model Settings Tab
        self.model_tab = QWidget()
        self.model_layout = QFormLayout(self.model_tab)
        self.tabs.addTab(self.model_tab, "Model Settings")

        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0, 2)
        self.temperature.setSingleStep(0.1)
        self.temperature.setValue(0.8)

        self.num_ctx = QSpinBox()
        self.num_ctx.setRange(1, 8192)
        self.num_ctx.setValue(2048)

        self.num_gpu = QSpinBox()
        self.num_gpu.setRange(0, 8)
        self.num_gpu.setValue(1)

        self.num_thread = QSpinBox()
        self.num_thread.setRange(1, 32)
        self.num_thread.setValue(4)

        self.top_k = QSpinBox()
        self.top_k.setRange(1, 100)
        self.top_k.setValue(40)

        self.top_p = QDoubleSpinBox()
        self.top_p.setRange(0, 1)
        self.top_p.setSingleStep(0.05)
        self.top_p.setValue(0.9)

        self.repeat_penalty = QDoubleSpinBox()
        self.repeat_penalty.setRange(0, 2)
        self.repeat_penalty.setSingleStep(0.1)
        self.repeat_penalty.setValue(1.1)

        self.repeat_last_n = QSpinBox()
        self.repeat_last_n.setRange(0, 2048)
        self.repeat_last_n.setValue(64)

        self.seed = QSpinBox()
        self.seed.setRange(-1, 2147483647)  # Changed to avoid overflow
        self.seed.setValue(-1)

        self.mirostat = QComboBox()
        self.mirostat.addItems(["0", "1", "2"])

        self.mirostat_tau = QDoubleSpinBox()
        self.mirostat_tau.setRange(0, 10)
        self.mirostat_tau.setSingleStep(0.1)
        self.mirostat_tau.setValue(5.0)

        self.mirostat_eta = QDoubleSpinBox()
        self.mirostat_eta.setRange(0, 1)
        self.mirostat_eta.setSingleStep(0.01)
        self.mirostat_eta.setValue(0.1)

        self.f16_kv = QCheckBox()
        self.logits_all = QCheckBox()
        self.vocab_only = QCheckBox()

        self.model_layout.addRow("Temperature:", self.temperature)
        self.model_layout.addRow("Context Length:", self.num_ctx)
        self.model_layout.addRow("Number of GPUs:", self.num_gpu)
        self.model_layout.addRow("Number of Threads:", self.num_thread)
        self.model_layout.addRow("Top K:", self.top_k)
        self.model_layout.addRow("Top P:", self.top_p)
        self.model_layout.addRow("Repeat Penalty:", self.repeat_penalty)
        self.model_layout.addRow("Repeat Last N:", self.repeat_last_n)
        self.model_layout.addRow("Seed:", self.seed)
        self.model_layout.addRow("Mirostat:", self.mirostat)
        self.model_layout.addRow("Mirostat Tau:", self.mirostat_tau)
        self.model_layout.addRow("Mirostat Eta:", self.mirostat_eta)
        self.model_layout.addRow("Use F16 KV:", self.f16_kv)
        self.model_layout.addRow("Logits All:", self.logits_all)
        self.model_layout.addRow("Vocab Only:", self.vocab_only)

        # UI Settings Tab
        self.ui_tab = QWidget()
        self.ui_layout = QFormLayout(self.ui_tab)
        self.tabs.addTab(self.ui_tab, "UI Settings")

        self.font_size = QSpinBox()
        self.font_size.setRange(8, 24)
        self.font_size.setValue(12)

        self.theme = QComboBox()
        self.theme.addItems(["Light", "Dark", "System"])

        self.chat_bubble_color = QComboBox()
        self.chat_bubble_color.addItems(["Blue", "Green", "Gray"])

        self.ui_layout.addRow("Font Size:", self.font_size)
        self.ui_layout.addRow("Theme:", self.theme)
        self.ui_layout.addRow("Chat Bubble Color:", self.chat_bubble_color)

        # Advanced Settings Tab
        self.advanced_tab = QWidget()
        self.advanced_layout = QFormLayout(self.advanced_tab)
        self.tabs.addTab(self.advanced_tab, "Advanced Settings")

        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(1, 8192)
        self.max_tokens.setValue(2048)

        self.stop_sequences = QLineEdit()
        self.stop_sequences.setPlaceholderText("Enter stop sequences separated by comma")

        self.presence_penalty = QDoubleSpinBox()
        self.presence_penalty.setRange(-2.0, 2.0)
        self.presence_penalty.setSingleStep(0.1)
        self.presence_penalty.setValue(0.0)

        self.frequency_penalty = QDoubleSpinBox()
        self.frequency_penalty.setRange(-2.0, 2.0)
        self.frequency_penalty.setSingleStep(0.1)
        self.frequency_penalty.setValue(0.0)

        self.advanced_layout.addRow("Max Tokens:", self.max_tokens)
        self.advanced_layout.addRow("Stop Sequences:", self.stop_sequences)
        self.advanced_layout.addRow("Presence Penalty:", self.presence_penalty)
        self.advanced_layout.addRow("Frequency Penalty:", self.frequency_penalty)

        # Memory Settings Tab
        self.memory_tab = QWidget()
        self.memory_layout = QFormLayout(self.memory_tab)
        self.tabs.addTab(self.memory_tab, "Memory Settings")

        self.memory_type = QComboBox()
        self.memory_type.addItems(["ConversationBufferMemory", "ConversationBufferWindowMemory", "ConversationSummaryMemory"])

        self.memory_k = QSpinBox()
        self.memory_k.setRange(1, 100)
        self.memory_k.setValue(5)

        self.memory_layout.addRow("Memory Type:", self.memory_type)
        self.memory_layout.addRow("Memory K:", self.memory_k)

        # Save Button
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.accept)
        self.layout.addWidget(self.save_button)

class ChatbotApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.stream_handler = StreamHandler()
        self.stream_handler.new_token.connect(self.update_chat_display)
        self.llm = None  # Initialize llm as None
        self.memory = ConversationBufferMemory()
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI assistant."),
            ("human", "{input}"),
            ("ai", "{output}"),
        ])
        self.chat_thread = None
        self.current_ai_message = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Ollama Chatbot v0.1')
        self.resize(600, 850)  # Set initial size
        self.center()  # Center the window on the screen
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)

        self.systemMessageLabel = QLabel()  # Add this line
        self.systemMessageLabel.setFont(QFont('Arial', 10))
        self.systemMessageLabel.setStyleSheet("color: gray;")
        main_layout.addWidget(self.systemMessageLabel)  # Add this line
        
        # Create menu bar
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        new_chat_action = QAction('New Chat', self)
        new_chat_action.setShortcut('Ctrl+N')
        new_chat_action.triggered.connect(self.new_chat)
        file_menu.addAction(new_chat_action)
        
        save_chat_action = QAction('Save Chat', self)
        save_chat_action.setShortcut('Ctrl+S')
        save_chat_action.triggered.connect(self.save_chat)
        file_menu.addAction(save_chat_action)
        
        load_chat_action = QAction('Load Chat', self)
        load_chat_action.setShortcut('Ctrl+O')
        load_chat_action.triggered.connect(self.load_chat)
        file_menu.addAction(load_chat_action)
        
        export_chat_action = QAction('Export Chat', self)
        export_chat_action.triggered.connect(self.export_chat)
        file_menu.addAction(export_chat_action)
        
        # Edit menu
        edit_menu = menubar.addMenu('Edit')
        
        clear_chat_action = QAction('Clear Chat', self)
        clear_chat_action.triggered.connect(self.clear_chat)
        edit_menu.addAction(clear_chat_action)
        
        copy_last_message_action = QAction('Copy Last Message', self)
        copy_last_message_action.setShortcut('Ctrl+C')
        copy_last_message_action.triggered.connect(self.copy_last_message)
        edit_menu.addAction(copy_last_message_action)
        
        # View menu
        view_menu = menubar.addMenu('View')
        
        toggle_dark_mode_action = QAction('Toggle Dark Mode', self)
        toggle_dark_mode_action.triggered.connect(self.toggle_dark_mode)
        view_menu.addAction(toggle_dark_mode_action)
        
        # Model menu
        model_menu = menubar.addMenu('Model')        
        change_model_action = QAction('Change Model', self)
        change_model_action.triggered.connect(self.change_model_dialog)
        model_menu.addAction(change_model_action)
        
        show_available_models_action = QAction('Show Available Models', self)
        show_available_models_action.triggered.connect(self.listModels)
        model_menu.addAction(show_available_models_action)
        
        # Settings menu
        settings_menu = menubar.addMenu('Settings')
        open_settings_action = QAction('Open Settings', self)
        open_settings_action.triggered.connect(self.open_settings)
        settings_menu.addAction(open_settings_action)

        show_system_info_action = QAction('Show System Info', self)  # Add this line
        show_system_info_action.triggered.connect(self.show_system_info)  # Add this line
        settings_menu.addAction(show_system_info_action)  # Add this line
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        self.chat_area = QScrollArea()
        self.chat_area.setWidgetResizable(True)
        self.chat_content = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_area.setWidget(self.chat_content)
        main_layout.addWidget(self.chat_area)
        
        input_layout = QHBoxLayout()
        
        self.inputField = QLineEdit()
        self.inputField.setPlaceholderText("Type your message here...")
        self.inputField.setFont(QFont('Arial', 12))
        self.inputField.returnPressed.connect(self.sendMessage)
        input_layout.addWidget(self.inputField)
        
        self.sendButton = QPushButton('Send')
        self.sendButton.setFont(QFont('Arial', 12))
        self.sendButton.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.sendButton.clicked.connect(self.sendMessage)
        input_layout.addWidget(self.sendButton)
        
        main_layout.addLayout(input_layout)
        
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#E5DDD5"))
        self.setPalette(palette)

        # Initialize the model
        self.change_model()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def open_settings(self):
        try:
            settings_dialog = SettingsDialog(self)
            if settings_dialog.exec_():
                # Update LLM settings
                self.change_model()
        except Exception as e:
            logging.error(f"Error opening settings: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to open settings: {str(e)}")

    def change_model(self):
        settings_dialog = self.findChild(SettingsDialog)
        if settings_dialog:
            try:
                self.llm = ChatOllama(
                    model="gemma2:2b",  # Default model
                    temperature=settings_dialog.temperature.value(),
                    num_ctx=settings_dialog.num_ctx.value(),
                    num_gpu=settings_dialog.num_gpu.value(),
                    num_thread=settings_dialog.num_thread.value(),
                    top_k=settings_dialog.top_k.value(),
                    top_p=settings_dialog.top_p.value(),
                    repeat_penalty=settings_dialog.repeat_penalty.value(),
                    repeat_last_n=settings_dialog.repeat_last_n.value(),
                    seed=settings_dialog.seed.value(),
                    mirostat=int(settings_dialog.mirostat.currentText()),
                    mirostat_tau=settings_dialog.mirostat_tau.value(),
                    mirostat_eta=settings_dialog.mirostat_eta.value(),
                    f16_kv=settings_dialog.f16_kv.isChecked(),
                    logits_all=settings_dialog.logits_all.isChecked(),
                    vocab_only=settings_dialog.vocab_only.isChecked(),
                    streaming=True,
                    callbacks=[self.stream_handler],
                )
                self.add_system_message("The gemma2:2b model is loaded")
            except Exception as e:
                logging.error(f"Error loading model: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to load model: {str(e)}")
                self.llm = None
        else:
            try:
                self.llm = ChatOllama(
                    model="gemma2:2b",  # Default model
                    temperature=0.8,
                    streaming=True,
                    callbacks=[self.stream_handler],
                )
                self.add_system_message("The gemma2:2b model is loaded")
            except Exception as e:
                logging.error(f"Error loading default model: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to load default model: {str(e)}")
                self.llm = None

    def add_system_message(self, message):
        try:
            self.systemMessageLabel.setText(message)  # Update this line
        except Exception as e:
            logging.error(f"Error adding system message: {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to add system message: {str(e)}")


    def sendMessage(self):
        userMessage = self.inputField.text().strip()
        if not userMessage:
            return
        
        self.add_message(userMessage, is_user=True)
        self.inputField.clear()
        
        if self.llm is None:
            QMessageBox.warning(self, "Warning", "Model not loaded. Please check your settings and try again.")
            return

        try:
            self.memory.chat_memory.add_user_message(userMessage)
            messages = self.prompt_template.format_messages(input=userMessage, output="")
            messages.extend(self.memory.chat_memory.messages)
            self.chat_thread = ChatThread(self.llm, messages)
            self.chat_thread.response_ready.connect(self.handleResponse)
            self.chat_thread.error_occurred.connect(self.handleError)
            self.chat_thread.start()
            self.current_ai_message = MessageWidget("", is_user=False)
            self.chat_layout.addWidget(self.current_ai_message)
        except Exception as e:
            logging.error(f"Error sending message: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to send message: {str(e)}")

    def handleResponse(self, response):
        try:
            if self.current_ai_message:
                self.current_ai_message.layout().itemAt(0).widget().setText(response)
                self.current_ai_message = None
                self.chat_area.verticalScrollBar().setValue(self.chat_area.verticalScrollBar().maximum())
                self.memory.chat_memory.add_ai_message(response)
        except Exception as e:
            logging.error(f"Error handling response: {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to handle response: {str(e)}")

    def handleError(self, error_message):
        try:
            if "404" in error_message and "pull the model" in error_message:
                model_name = error_message.split("`ollama pull ")[-1].split("`")[0]
                reply = QMessageBox.question(self, "Model Not Found", 
                                             f"The model {model_name} is not found. Do you want to pull it?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.Yes:
                    self.pullModel(model_name)
            else:
                QMessageBox.critical(self, "Error", f"{error_message}")
        except Exception as e:
            logging.error(f"Error handling error message: {str(e)}")
            QMessageBox.critical(self, "Critical Error", f"Failed to handle error message: {str(e)}")


    def listModels(self):
        ollama_path = self.find_ollama_executable()

        if not ollama_path:
            QMessageBox.critical(self, "Error", "Ollama executable not found. Please ensure Ollama is installed and added to your system's PATH.")
            return

        try:
            if sys.platform.startswith('win'):
                # Use PowerShell to run the command and keep the window open
                powershell_command = f'Start-Process powershell -ArgumentList "-NoExit", "-Command", "& \'{ollama_path}\' list"'
                subprocess.Popen(['powershell', '-Command', powershell_command], creationflags=subprocess.CREATE_NEW_CONSOLE)
            elif sys.platform.startswith('darwin'):  # macOS
                subprocess.Popen(['open', '-a', 'Terminal', ollama_path, 'list'])
            else:  # Linux/Unix
                subprocess.Popen(['x-terminal-emulator', '-e', f'{ollama_path} list'])

        except Exception as e:
            logging.error(f"Error listing models: {str(e)}")
            QMessageBox.critical(self, "Error", f"An error occurred while trying to list models: {str(e)}\nPlease check your Ollama installation and try again.")

    def pullModel(self, model_name):
        ollama_path = self.find_ollama_executable()

        if not ollama_path:
            QMessageBox.critical(self, "Error", "Ollama executable not found. Please ensure Ollama is installed and added to your system's PATH.")
            return

        try:
            if sys.platform.startswith('win'):
                # Use PowerShell to run the command and keep the window open
                powershell_command = f'Start-Process powershell -ArgumentList "-NoExit", "-Command", "& \'{ollama_path}\' pull {model_name}"'
                subprocess.Popen(['powershell', '-Command', powershell_command], creationflags=subprocess.CREATE_NEW_CONSOLE)
            elif sys.platform.startswith('darwin'):  # macOS
                subprocess.Popen(['open', '-a', 'Terminal', ollama_path, 'pull', model_name])
            else:  # Linux/Unix
                subprocess.Popen(['x-terminal-emulator', '-e', f'{ollama_path} pull {model_name}'])

            QMessageBox.information(self, "Model Download", f"Downloading {model_name}. Please check the opened terminal for progress.")

        except Exception as e:
            logging.error(f"Error pulling model: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to start model download: {str(e)}")

    def find_ollama_executable(self):
        """
        Finds the path to the 'ollama' executable.
        """
        possible_names = ['ollama']
        if sys.platform.startswith('win'):
            possible_names = ['ollama.exe']

        paths_to_search = []
        if sys.platform.startswith('win'):
            # Common installation paths on Windows
            paths_to_search.extend([
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Ollama', 'ollama.exe'),
                os.path.join(os.environ.get('ProgramFiles', ''), 'Ollama', 'ollama.exe')
            ])
        else:
            # Common installation paths on Unix/Linux/Mac
            paths_to_search.extend([
                '/usr/local/bin/ollama',
                '/usr/bin/ollama',
                os.path.expanduser('~/bin/ollama')
            ])

        # Search specified paths
        for name in possible_names:
            for path in paths_to_search:
                if shutil.which(name):
                    return shutil.which(name)
                if os.path.isfile(path):
                    return path

        # Fallback to shutil.which
        return shutil.which(possible_names[0])

    def update_chat_display(self, token: str):
        try:
            if self.current_ai_message:
                current_text = self.current_ai_message.layout().itemAt(0).widget().text()
                self.current_ai_message.layout().itemAt(0).widget().setText(current_text + token)
                self.chat_area.verticalScrollBar().setValue(self.chat_area.verticalScrollBar().maximum())
        except Exception as e:
            logging.error(f"Error updating chat display: {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to update chat display: {str(e)}")

    def add_message(self, message, is_user=True):
        try:
            message_widget = MessageWidget(message, is_user)
            self.chat_layout.addWidget(message_widget)
            self.chat_area.verticalScrollBar().setValue(self.chat_area.verticalScrollBar().maximum())
        except Exception as e:
            logging.error(f"Error adding message: {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to add message: {str(e)}")

    def new_chat(self):
        try:
            self.memory = ConversationBufferMemory()
            self.clear_chat()
            self.add_system_message("New chat started")
        except Exception as e:
            logging.error(f"Error starting new chat: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to start new chat: {str(e)}")

    def save_chat(self):
        try:
            file_name, _ = QFileDialog.getSaveFileName(self, "Save Chat", "", "JSON Files (*.json)")
            if file_name:
                chat_data = {
                    "messages": [{"type": msg.type, "content": msg.content} for msg in self.memory.chat_memory.messages],
                    "model": "gemma2:2b"  # Default model
                }
                with open(file_name, 'w') as f:
                    json.dump(chat_data, f)
                self.add_system_message(f"Chat saved to {file_name}")
        except Exception as e:
            logging.error(f"Error saving chat: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save chat: {str(e)}")

    def load_chat(self):
        try:
            file_name, _ = QFileDialog.getOpenFileName(self, "Load Chat", "", "JSON Files (*.json)")
            if file_name:
                with open(file_name, 'r') as f:
                    chat_data = json.load(f)
                self.memory.chat_memory.messages = [
                    (msg["type"], msg["content"]) for msg in chat_data["messages"]
                ]
                self.change_model()
                self.clear_chat()
                for msg_type, content in self.memory.chat_memory.messages:
                    self.add_message(content, is_user=(msg_type == "human"))
                self.add_system_message(f"Chat loaded from {file_name}")
        except Exception as e:
            logging.error(f"Error loading chat: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load chat: {str(e)}")

    def export_chat(self):
        try:
            file_name, _ = QFileDialog.getSaveFileName(self, "Export Chat", "", "Text Files (*.txt)")
            if file_name:
                with open(file_name, 'w') as f:
                    for message in self.memory.chat_memory.messages:
                        f.write(f"{'User' if message.type == 'human' else 'AI'}: {message.content}\n\n")
                self.add_system_message(f"Chat exported to {file_name}")
        except Exception as e:
            logging.error(f"Error exporting chat: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to export chat: {str(e)}")

    def clear_chat(self):
        try:
            for i in reversed(range(self.chat_layout.count())): 
                self.chat_layout.itemAt(i).widget().setParent(None)
        except Exception as e:
            logging.error(f"Error clearing chat: {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to clear chat: {str(e)}")

    def copy_last_message(self):
        try:
            if self.chat_layout.count() > 0:
                last_message = self.chat_layout.itemAt(self.chat_layout.count() - 1).widget()
                QApplication.clipboard().setText(last_message.layout().itemAt(0).widget().text())
                self.add_system_message("Last message copied to clipboard")
            else:
                QMessageBox.warning(self, "Warning", "No messages to copy")
        except Exception as e:
            logging.error(f"Error copying last message: {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to copy last message: {str(e)}")

    def change_model_dialog(self):
        try:
            models = [
                "smollm:135m", "smollm:360m", "qwen2.5:0.5b", "qwen2.5:1.5b",
                "deepseek-coder:1.3b", "yi-coder:1.5b", "stablelm2:1.6b",
                "smollm:1.7b", "gemma2:2b", "qwen2.5:3b", "phi3.5:3.8b",
                "yi:6b", "deepseek-coder:6.7b", "qwen2.5:7b", "llama3.1:8b",
                "gemma2:9b", "yi:9b", "yi-coder:9b", "mistral-nemo:12b",
                "qwen2.5:14b", "gemma2:27b"
            ]
            default_model = "gemma2:2b"
            default_index = models.index(default_model)
            model, ok = QInputDialog.getItem(self, 'Change Model', 'Select a model:', models, default_index, False)
            if ok and model:
                self.llm = ChatOllama(
                    model=model,
                    temperature=self.temperature.value(),
                    streaming=True,
                    callbacks=[self.stream_handler],
                )
                self.add_system_message(f"Model changed to {model}")
        except Exception as e:
            logging.error(f"Error changing model: {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to change model: {str(e)}")

    def open_settings(self):
        try:
            settings_dialog = SettingsDialog(self)
            if settings_dialog.exec_():
                # Update LLM settings
                self.change_model()
        except Exception as e:
            logging.error(f"Error opening settings: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to open settings: {str(e)}")

    def show_system_info(self):
        try:
            # Get CPU information
            cpu_info = platform.processor()
            cpu_cores = psutil.cpu_count(logical=True)
            cpu_freq = psutil.cpu_freq().current

            # Get RAM information
            ram = psutil.virtual_memory()
            total_ram = ram.total / (1024 ** 3)
            available_ram = ram.available / (1024 ** 3)

            # Get GPU information (if available)
            gpus = GPUtil.getGPUs()
            gpu_info = ""
            total_gpu_vram = 0
            if gpus:
                for gpu in gpus:
                    gpu_info += f"<li>Name: {gpu.name}</li>"
                    gpu_info += f"<li>VRAM: {gpu.memoryTotal:.2f} GB</li>"
                    total_gpu_vram += gpu.memoryTotal
            else:
                gpu_info = "<li>No GPU detected.</li>"

            # Start of Selection
            # Estimate maximum model size based on available RAM and GPU VRAM
            # Assuming 0.6 GB per billion parameters (Q4_0 quantization) with additional overhead

            bytes_per_billion_params = 0.6  # GB per billion parameters

            # Calculate model size based on available RAM
            ram_model_size = available_ram / bytes_per_billion_params

            # Calculate model size based on GPU VRAM, if available
            if gpus:
                gpu_model_size = total_gpu_vram / bytes_per_billion_params
            else:
                gpu_model_size = float('inf')  # No GPU limit if GPU is not available

            # The maximum model size is constrained by both RAM and GPU VRAM
            max_model_size = min(ram_model_size, gpu_model_size)

            if max_model_size >= 1:
                model_size_unit = "B"
            else:
                max_model_size = int(max_model_size * 1000)  # Convert to millions
                model_size_unit = "M"

            # Create a colorful HTML message for system information
            html_message = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    h2 {{ color: #2c3e50; }}
                    .info {{ margin-left: 20px; }}
                    .highlight {{ color: #27ae60; font-weight: bold; }}
                </style>
            </head>
            <body>
                <h2>System Information</h2>
                <div class="info">
                    <h3>CPU</h3>
                    <ul>
                        <li>Processor: {cpu_info}</li>
                        <li>Cores: {cpu_cores}</li>
                        <li>Frequency: {cpu_freq:.2f} GHz</li>
                    </ul>
                    <h3>RAM</h3>
                    <ul>
                        <li>Total: {total_ram:.2f} GB</li>
                        <li>Available: {available_ram:.2f} GB</li>
                    </ul>
                    <h3>GPU</h3>
                    <ul>
                        {gpu_info}
                    </ul>
                    <h3>Estimated Maximum Model Size (Q4_0 Quantization)</h3>
                    <p>Based on your hardware, you can likely run models up to <span class="highlight">{round(max_model_size, 1)} {model_size_unit}</span> parameters locally using Q4_0 quantization.</p>
                    <p>Note: This estimate assumes Q4_0 quantization and is approximate. Actual performance may vary depending on other factors.</p>
                </div>
            </body>
            </html>
            """

            # Display the system information in a message box with HTML formatting
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("System Information")
            msg_box.setText(html_message)
            msg_box.setTextFormat(Qt.RichText)
            msg_box.exec_()

        except Exception as e:
            logging.error(f"Error showing system info: {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to show system info: {str(e)}")

    def save_chat(self):
        try:
            file_name, _ = QFileDialog.getSaveFileName(self, "Save Chat", "", "JSON Files (*.json)")
            if file_name:
                chat_data = {
                    "messages": [{"type": msg.type, "content": msg.content} for msg in self.memory.chat_memory.messages],
                    "model": self.llm.model if self.llm else "gemma2:2b"  # Use current model or default
                }
                with open(file_name, 'w') as f:
                    json.dump(chat_data, f)
                self.add_system_message(f"Chat saved to {file_name}")
        except Exception as e:
            logging.error(f"Error saving chat: {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to save chat: {str(e)}")

    def load_chat(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Chat", "", "JSON Files (*.json)")
        if file_name:
            with open(file_name, 'r') as f:
                chat_data = json.load(f)
            self.memory.chat_memory.messages = [
                (msg["type"], msg["content"]) for msg in chat_data["messages"]
            ]
            self.change_model()
            self.clear_chat()
            for msg_type, content in self.memory.chat_memory.messages:
                self.add_message(content, is_user=(msg_type == "human"))
            self.add_system_message(f"Chat loaded from {file_name}")

    def export_chat(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Export Chat", "", "Text Files (*.txt)")
        if file_name:
            with open(file_name, 'w') as f:
                for message in self.memory.chat_memory.messages:
                    f.write(f"{'User' if message.type == 'human' else 'AI'}: {message.content}\n\n")
            self.add_system_message(f"Chat exported to {file_name}")

    def clear_chat(self):
        for i in reversed(range(self.chat_layout.count())): 
            self.chat_layout.itemAt(i).widget().setParent(None)

    def copy_last_message(self):
        if self.chat_layout.count() > 0:
            last_message = self.chat_layout.itemAt(self.chat_layout.count() - 1).widget()
            QApplication.clipboard().setText(last_message.layout().itemAt(0).widget().text())
            self.add_system_message("Last message copied to clipboard")

    def toggle_dark_mode(self):
        if self.palette().color(QPalette.Window).lightness() > 128:
            # Switch to dark mode
            palette = QPalette()
            # Window background (Deep navy blue)
            palette.setColor(QPalette.Window, QColor("#1A1A2E"))
            # Window text (Light gray)
            palette.setColor(QPalette.WindowText, QColor("#E0E0E0"))
            # Base color for widgets (Darker navy blue)
            palette.setColor(QPalette.Base, QColor("#16213E"))
            # Alternate base color (Rich dark blue)
            palette.setColor(QPalette.AlternateBase, QColor("#0F3460"))
            # Tooltip background (Darker navy blue)
            palette.setColor(QPalette.ToolTipBase, QColor("#16213E"))
            # Tooltip text (Light gray)
            palette.setColor(QPalette.ToolTipText, QColor("#E0E0E0"))
            # Text color (Black)
            palette.setColor(QPalette.Text, QColor("#000000"))
            # Button color (Rich dark blue)
            palette.setColor(QPalette.Button, QColor("#0F3460"))
            # Button text (Light gray)
            palette.setColor(QPalette.ButtonText, QColor("#E0E0E0"))
            # Bright text (Vibrant pink)
            palette.setColor(QPalette.BrightText, QColor("#E94560"))
            # Link color (Bright blue)
            palette.setColor(QPalette.Link, QColor("#4D9DE0"))
            # Highlight color (Bright blue)
            palette.setColor(QPalette.Highlight, QColor("#4D9DE0"))
            # Highlighted text (Deep navy blue)
            palette.setColor(QPalette.HighlightedText, QColor("#1A1A2E"))
            self.setPalette(palette)
            
            # Set menu bar background to dark color
            self.menuBar().setStyleSheet("QMenuBar { background-color: #0F3460; color: #E0E0E0; }")
        else:
            # Switch to light mode
            palette = QPalette()
            # Window background (Light gray)
            palette.setColor(QPalette.Window, QColor("#F5F5F5"))
            # Window text (Dark gray)
            palette.setColor(QPalette.WindowText, QColor("#212121"))
            # Base color for widgets (White)
            palette.setColor(QPalette.Base, QColor("#FFFFFF"))
            # Alternate base color (Light gray)
            palette.setColor(QPalette.AlternateBase, QColor("#E0E0E0"))
            # Tooltip background (White)
            palette.setColor(QPalette.ToolTipBase, QColor("#FFFFFF"))
            # Tooltip text (Dark gray)
            palette.setColor(QPalette.ToolTipText, QColor("#212121"))
            # Text color (Dark gray)
            palette.setColor(QPalette.Text, QColor("#212121"))
            # Button color (Light gray)
            palette.setColor(QPalette.Button, QColor("#E0E0E0"))
            # Button text (Dark gray)
            palette.setColor(QPalette.ButtonText, QColor("#212121"))
            # Bright text (Red)
            palette.setColor(QPalette.BrightText, QColor("#D32F2F"))
            # Link color (Blue)
            palette.setColor(QPalette.Link, QColor("#1976D2"))
            # Highlight color (Light blue)
            palette.setColor(QPalette.Highlight, QColor("#2196F3"))
            # Highlighted text (White)
            palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
            self.setPalette(palette)

            # Reset menu bar background to light color
            self.menuBar().setStyleSheet("QMenuBar { background-color: #F5F5F5; color: #212121; }")

    def change_model_dialog(self):
        try:
            models = [
                "smollm:135m", "smollm:360m", "qwen2.5:0.5b", "qwen2.5:1.5b",
                "deepseek-coder:1.3b", "yi-coder:1.5b", "stablelm2:1.6b",
                "smollm:1.7b", "gemma2:2b", "qwen2.5:3b", "phi3.5:3.8b",
                "yi:6b", "deepseek-coder:6.7b", "qwen2.5:7b", "llama3.1:8b",
                "gemma2:9b", "yi:9b", "yi-coder:9b", "mistral-nemo:12b",
                "qwen2.5:14b", "gemma2:27b"
            ]
            default_model = "gemma2:2b"
            default_index = models.index(default_model)

            dialog = QDialog(self)
            dialog.setWindowTitle("Change Model")
            layout = QVBoxLayout(dialog)

            model_combo = QComboBox()
            model_combo.addItems(models)
            model_combo.setCurrentIndex(default_index)
            layout.addWidget(model_combo)

            custom_model_checkbox = QCheckBox("Enter custom model name:")
            layout.addWidget(custom_model_checkbox)

            custom_model_edit = QLineEdit()
            custom_model_edit.setEnabled(False)  # Initially disabled
            layout.addWidget(custom_model_edit)

            # Connect checkbox to enable/disable the line edit
            custom_model_checkbox.stateChanged.connect(lambda state: custom_model_edit.setEnabled(state == Qt.Checked))

            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, dialog)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            if dialog.exec_() == QDialog.Accepted:
                if custom_model_checkbox.isChecked():
                    model = custom_model_edit.text().strip()
                else:
                    model = model_combo.currentText()

                if model:
                    try:
                        self.llm = ChatOllama(
                            model=model,
                            streaming=True,
                            callbacks=[self.stream_handler],
                        )
                        self.add_system_message(f"The {model} model is loaded")
                    except Exception as e:
                        logging.error(f"Error loading model: {str(e)}")
                        QMessageBox.critical(self, "Error", f"Failed to load model: {str(e)}")
                        self.llm = None

        except Exception as e:
            logging.error(f"Error changing model: {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to change model: {str(e)}")

    def show_about(self):
        QMessageBox.about(self, "About Ollama Chatbot", 
                          "Ollama Chatbot v2.2\n\n"
                          "A simple chatbot interface for Ollama models.\n"
                          "Created using PyQt5 and LangChain.\n\n"
                          "© 2024 github.com/mshojaei77")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    chatbot = ChatbotApp()
    chatbot.show()
    sys.exit(app.exec_())
