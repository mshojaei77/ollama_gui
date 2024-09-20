import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit,
    QPushButton, QHBoxLayout, QLabel, QScrollArea, QDesktopWidget,
    QMainWindow, QAction, QMenu, QDialog, QFormLayout, QDoubleSpinBox,
    QSpinBox, QComboBox, QCheckBox, QTabWidget, QSizePolicy, QFrame,
    QFileDialog, QInputDialog, QMessageBox, QDialogButtonBox, QTextEdit
)
from PyQt5.QtGui import QFont, QPalette, QColor, QTextCursor
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QThread
from langchain_community.chat_models import ChatOllama
from langchain.callbacks.base import BaseCallbackHandler
from langchain.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferMemory, ConversationBufferWindowMemory, ConversationSummaryMemory
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

import os
import json
import appdirs
import uuid  
import shutil
import wmi
import GPUtil
import sys
import logging
import winreg

# Set up logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Set environment variable for CUDA
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # Replace with desired GPU ID

# Global variables for settings
CONFIG_DIR = appdirs.user_config_dir("OllamaChatbot")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
# Default settings
DEFAULT_SETTINGS = {
    "model": "gemma2:2b",
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
# Function to load settings
def load_settings():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_SETTINGS.copy()

# Function to save settings
def save_settings(settings):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

# Global settings variable
SETTINGS = load_settings()

# Run Ollama in PowerShell
if sys.platform.startswith('win'):
    try:
        subprocess.Popen(['powershell', '-Command', 'ollama list'], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        logging.error(f"Failed to start Ollama: {str(e)}")
        QMessageBox.warning(None, "Warning", f"Failed to start Ollama: {str(e)}\nPlease ensure Ollama is installed and accessible from PowerShell.")

class CustomConversationBufferMemory(ConversationBufferMemory):
    def edit_message(self, message_id, new_content):
        for msg in self.chat_memory.messages:
            if getattr(msg, 'id', None) == message_id:
                msg.content = new_content

                break

class StreamHandler(QObject, BaseCallbackHandler):
    new_token = pyqtSignal(str)

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        try:
            self.new_token.emit(token)
        except Exception as e:
            logging.error(f"Error in StreamHandler: {str(e)}")

class ChatThread(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, llm, messages):
        super().__init__()
        self.llm = llm
        self.messages = messages
    
    def run(self):
        try:
            # Set no_proxy for localhost to avoid potential 503 errors
            os.environ['no_proxy'] = 'localhost,127.0.0.1'
            response = self.llm.invoke(self.messages)
            self.response_ready.emit(response.content)
        except Exception as e:
            logging.error(f"Error in ChatThread: {str(e)}")
            if "503" in str(e):
                self.error_occurred.emit("Oops! We couldn't connect to Ollama on your computer. This might be because of a VPN or proxy. Please try turning off any VPN or proxy you're using, and then try again.")
            else:
                self.error_occurred.emit(str(e))
    
    
    def sendMessage(self):
        try:
            userMessage = self.inputField.text().strip()
            if not userMessage:
                return
            
            self.add_message(userMessage, is_user=True)
            self.inputField.clear()
            
            if self.llm is None:
                QMessageBox.warning(self, "Warning", "Model not loaded. Please check your settings and try again.")
                return

            self.memory.chat_memory.add_user_message(userMessage)
            messages = self.prompt_template.format_messages(input=userMessage, output="")
            messages.extend(self.memory.chat_memory.messages)
            self.chat_thread = ChatThread(self.llm, messages)
            self.chat_thread.response_ready.connect(self.handleResponse)
            self.chat_thread.error_occurred.connect(self.handleError)
            self.chat_thread.start()
            
            # Create a placeholder for AI message
            self.current_ai_message = MessageWidget("", is_user=False, chat_app=self)
            self.current_ai_message.message_id = uuid.uuid4().hex  # Assign a unique ID
            self.chat_layout.addWidget(self.current_ai_message)
        except Exception as e:
            logging.error(f"Error sending message: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to send message: {str(e)}")
            


class MessageWidget(QWidget):
    def __init__(self, message, is_user, chat_app=None, message_id=None):
        super().__init__()
        self.chat_app = chat_app
        self.message_id = message_id if message_id else uuid.uuid4().hex
        self.is_user = is_user
        self.is_editing = False

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)

        self.text = QTextEdit()
        self.text.setMarkdown(message)
        self.text.setReadOnly(True)
        self.text.setFont(QFont('SF Pro Text', 13))
        self.text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text.setFrameStyle(QFrame.NoFrame)
        
        self.text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        self.text.document().contentsChanged.connect(self.adjust_size)

        if is_user:
            self.text.setStyleSheet("""
                QTextEdit {
                    background-color: #F0F8FF;
                    border: none;
                    border-radius: 18px;
                    padding: 15px 20px;  /* Increased padding */
                    color: #333333;
                }
            """)
        else:
            self.text.setStyleSheet("""
                QTextEdit {
                    background-color: #D8E4FF;
                    border: none;
                    border-radius: 18px;
                    padding: 15px 20px;  /* Increased padding */
                    color: #333333;
                }
            """)

        text_container = QHBoxLayout()
        self.edit_button = QPushButton("Edit")
        self.edit_button.setFixedSize(70, 30)
        self.edit_button.clicked.connect(self.toggle_edit_mode)
        self.edit_button.setStyleSheet("""
            QPushButton {
                background-color: #87CEFA;
                color: #333333;
                border: none;
                border-radius: 15px;
                padding: 5px 10px;
                font-family: 'SF Pro Text';
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #6495ED;
            }
            QPushButton:pressed {
                background-color: #4169E1;
            }
        """)

        if is_user:
            text_container.addStretch()
            text_container.addWidget(self.edit_button)
            text_container.addWidget(self.text)
        else:
            text_container.addWidget(self.text)
            text_container.addWidget(self.edit_button)
            text_container.addStretch()

        layout.addLayout(text_container)

        self.setLayout(layout)
        self.setContentsMargins(0, 5, 0, 5)

        # Initial size adjustment
        self.adjust_size()

    def adjust_size(self):
        doc = self.text.document()
        doc.setTextWidth(self.text.viewport().width())
        doc_height = doc.size().height()
        
        max_width = min(int(self.chat_app.width() * 0.9) if self.chat_app else 900, 900)  # Increased max_width
        min_width = max(int(self.chat_app.width() * 0.2) if self.chat_app else 300, 300)
        
        new_width = max(min(int(doc.idealWidth()) + 50, max_width), min_width)  # Adjusted width calculation, added more padding
        new_height = int(doc_height) + 40  # Adjusted height calculation
        
        self.text.setMinimumWidth(min_width)
        self.text.setMaximumWidth(max_width)
        self.text.setFixedHeight(new_height)
        self.setFixedHeight(new_height + 20)  # Increased height of the container

        # Force layout update
        self.updateGeometry()
        if self.parent():
            self.parent().updateGeometry()

    def toggle_edit_mode(self):
        try:
            if not self.is_editing:
                self.is_editing = True
                self.text.setReadOnly(False)
                self.edit_button.setText("Save")
                self.edit_button.setStyleSheet("""
                    QPushButton {
                        background-color: #98FB98;  /* Pale Green */
                        color: #333333;
                        border: none;
                        border-radius: 15px;
                        padding: 5px 10px;
                        font-family: 'SF Pro Text';
                        font-size: 13px;
                        font-weight: 500;
                    }
                    QPushButton:hover {
                        background-color: #90EE90;  /* Light Green */
                    }
                    QPushButton:pressed {
                        background-color: #3CB371;  /* Medium Sea Green */
                    }
                """)
            else:
                new_content = self.text.toPlainText().strip()
                if new_content:
                    self.is_editing = False
                    self.text.setReadOnly(True)
                    self.edit_button.setText("Edit")
                    self.edit_button.setStyleSheet("""
                        QPushButton {
                            background-color: #87CEFA;  /* Light Sky Blue */
                            color: #333333;
                            border: none;
                            border-radius: 15px;
                            padding: 5px 10px;
                            font-family: 'SF Pro Text';
                            font-size: 13px;
                            font-weight: 500;
                        }
                        QPushButton:hover {
                            background-color: #6495ED;  /* Cornflower Blue */
                        }
                        QPushButton:pressed {
                            background-color: #4169E1;  /* Royal Blue */
                        }
                    """)
                    if self.chat_app:
                        self.chat_app.update_message(self.message_id, new_content)
                else:
                    QMessageBox.warning(self, "Warning", "Message cannot be empty.")
        except Exception as e:
            logging.error(f"Error toggling edit mode: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to edit message: {str(e)}")


class CustomTextEdit(QTextEdit):
    def __init__(self, parent=None, chat_app=None):
        super().__init__(parent)
        self.chat_app = chat_app  # Store a reference to the ChatbotApp instance
        self.setFixedHeight(100)  # Set a fixed height for the text edit
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Ensure it behaves like a single-line input
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)  # Always show the vertical scrollbar

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() == Qt.ShiftModifier:
                # Insert a new line
                cursor = self.textCursor()
                cursor.insertText('\n')
                self.setTextCursor(cursor)
            else:
                if self.chat_app:
                    self.chat_app.sendMessage()
                event.accept()
                return
        else:
            super().keyPressEvent(event)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.setWindowTitle("Settings")
            self.resize(600, 400)
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

            self.ui_layout.addRow("Font Size:", self.font_size)
            self.ui_layout.addRow("Theme:", self.theme)

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

            # System Prompt
            self.system_prompt = QTextEdit()
            self.system_prompt.setPlaceholderText("Enter system prompt here...")
            self.model_layout.addRow("System Prompt:", self.system_prompt)

            # Save Button
            self.save_button = QPushButton("Save")
            self.save_button.clicked.connect(self.accept)
            self.layout.addWidget(self.save_button)
            self.load_settings_to_ui()

        except Exception as e:
            logging.error(f"Error in SettingsDialog: {str(e)}")

    def load_settings_to_ui(self):
        self.temperature.setValue(SETTINGS['temperature'])
        self.num_ctx.setValue(SETTINGS['num_ctx'])
        self.num_gpu.setValue(SETTINGS['num_gpu'])
        self.num_thread.setValue(SETTINGS['num_thread'])
        self.top_k.setValue(SETTINGS['top_k'])
        self.top_p.setValue(SETTINGS['top_p'])
        self.repeat_penalty.setValue(SETTINGS['repeat_penalty'])
        self.repeat_last_n.setValue(SETTINGS['repeat_last_n'])
        self.seed.setValue(SETTINGS['seed'])
        self.mirostat.setCurrentText(str(SETTINGS['mirostat']))
        self.mirostat_tau.setValue(SETTINGS['mirostat_tau'])
        self.mirostat_eta.setValue(SETTINGS['mirostat_eta'])
        self.f16_kv.setChecked(SETTINGS['f16_kv'])
        self.logits_all.setChecked(SETTINGS['logits_all'])
        self.vocab_only.setChecked(SETTINGS['vocab_only'])
        self.font_size.setValue(SETTINGS['font_size'])
        self.theme.setCurrentText(SETTINGS['theme'])
        self.max_tokens.setValue(SETTINGS['max_tokens'])
        self.stop_sequences.setText(SETTINGS['stop_sequences'])
        self.presence_penalty.setValue(SETTINGS['presence_penalty'])
        self.frequency_penalty.setValue(SETTINGS['frequency_penalty'])
        self.memory_type.setCurrentText(SETTINGS['memory_type'])
        self.memory_k.setValue(SETTINGS['memory_k'])
        self.system_prompt.setPlainText(SETTINGS.get('system_prompt', ''))

    def accept(self):
        # Update global settings
        global SETTINGS
        SETTINGS.update({
            'model': SETTINGS['model'],  # Keep the current model
            'temperature': self.temperature.value(),
            'num_ctx': self.num_ctx.value(),
            'num_gpu': self.num_gpu.value(),
            'num_thread': self.num_thread.value(),
            'top_k': self.top_k.value(),
            'top_p': self.top_p.value(),
            'repeat_penalty': self.repeat_penalty.value(),
            'repeat_last_n': self.repeat_last_n.value(),
            'seed': self.seed.value(),
            'mirostat': int(self.mirostat.currentText()),
            'mirostat_tau': self.mirostat_tau.value(),
            'mirostat_eta': self.mirostat_eta.value(),
            'f16_kv': self.f16_kv.isChecked(),
            'logits_all': self.logits_all.isChecked(),
            'vocab_only': self.vocab_only.isChecked(),
            'font_size': self.font_size.value(),
            'theme': self.theme.currentText(),
            'max_tokens': self.max_tokens.value(),
            'stop_sequences': self.stop_sequences.text(),
            'presence_penalty': self.presence_penalty.value(),
            'frequency_penalty': self.frequency_penalty.value(),
            'memory_type': self.memory_type.currentText(),
            'memory_k': self.memory_k.value(),
            'system_prompt': self.system_prompt.toPlainText()
        })
        save_settings(SETTINGS)
        super().accept()
class ChatbotApp(QMainWindow):
    def __init__(self):
        super().__init__()
        try:
            self.stream_handler = StreamHandler()
            self.stream_handler.new_token.connect(self.update_chat_display)
            self.llm = None  # Initialize llm as None
            self.memory = CustomConversationBufferMemory()
            self.prompt_template = ChatPromptTemplate.from_messages([
                ("system", SETTINGS.get('system_prompt', "You are a helpful AI assistant.")),
                ("human", "{input}"),
                ("ai", "{output}"),
            ])
            self.chat_thread = None
            self.current_ai_message = None
            self.initUI()
            self.apply_settings()
        except Exception as e:
            logging.error(f"Error in ChatbotApp initialization: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to initialize the application: {str(e)}")


    def apply_settings(self):
        try:
            # Apply font size
            self.setStyleSheet(f"font-size: {SETTINGS['font_size']}px;")
            
            # Apply theme
            if SETTINGS['theme'] == 'Dark':
                self.toggle_dark_mode()
            elif SETTINGS['theme'] == 'Light':
                self.toggle_light_mode()
            elif SETTINGS['theme'] == 'System':
                self.apply_system_theme()
        
            
            # Update LLM settings
            self.change_model()
            
            # Update memory settings
            self.update_memory_settings()
            
            # Apply model-specific settings
            if self.llm:
                supported_attrs = [
                    'temperature', 'num_ctx', 'num_gpu', 'num_thread',
                    'top_k', 'top_p', 'repeat_penalty', 'repeat_last_n',
                    'seed', 'mirostat', 'mirostat_tau', 'mirostat_eta',
                    'f16_kv', 'logits_all', 'vocab_only'
                ]
                for attr in supported_attrs:
                    if hasattr(self.llm, attr):
                        setattr(self.llm, attr, SETTINGS[attr])
            
            # Update system message
            self.add_system_message(f"Settings applied successfully. Using model: {SETTINGS['model']}")
            
        except Exception as e:
            logging.error(f"Error applying settings: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to apply settings: {str(e)}")

    def change_model(self):
        try:
            self.llm = ChatOllama(
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
                callbacks=[self.stream_handler],
            )
            self.add_system_message(f"The {SETTINGS['model']} model is loaded")
        except Exception as e:
            logging.error(f"Error changing model: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to change model: {str(e)}")
            self.llm = None

    def update_memory_settings(self):
        memory_type = SETTINGS['memory_type']
        memory_k = SETTINGS['memory_k']
        
        if memory_type == "ConversationBufferMemory":
            self.memory = ConversationBufferMemory()
        elif memory_type == "ConversationBufferWindowMemory":
            self.memory = ConversationBufferWindowMemory(k=memory_k)
        elif memory_type == "ConversationSummaryMemory":
            self.memory = ConversationSummaryMemory(llm=self.llm)
        
        # Transfer existing messages to the new memory
        for message in self.memory.chat_memory.messages:
            self.memory.chat_memory.add_message(message)

    def update_memory_settings(self):
        memory_type = SETTINGS['memory_type']
        memory_k = SETTINGS['memory_k']
        
        if memory_type == "ConversationBufferMemory":
            self.memory = ConversationBufferMemory()
        elif memory_type == "ConversationBufferWindowMemory":
            self.memory = ConversationBufferWindowMemory(k=memory_k)
        elif memory_type == "ConversationSummaryMemory":
            self.memory = ConversationSummaryMemory(llm=self.llm)
        
        # Transfer existing messages to the new memory
        for message in self.memory.chat_memory.messages:
            self.memory.chat_memory.add_message(message)

    def open_settings(self):
        try:
            settings_dialog = SettingsDialog(self)
            if settings_dialog.exec_():
                # Apply settings immediately
                self.apply_settings()
        except Exception as e:
            logging.error(f"Error opening settings: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to open settings: {str(e)}")



    def initUI(self):
        try:
            self.setWindowTitle('Ollama Chatbot v0.2')
            self.resize(1000, 900)  # Set initial size
            self.center()  # Center the window on the screen
            
            # Create central widget and main layout
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QVBoxLayout(central_widget)
            main_layout.setSpacing(15)
            
            top_bar_layout = QHBoxLayout()
            
            # Add New Chat button
            self.new_chat_button = QPushButton('New Chat')
            self.new_chat_button.setStyleSheet("""
                QPushButton {
                    background-color: #2ecc71;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #27ae60;
                }
                QPushButton:pressed {
                    background-color: #229954;
                }
            """)
            self.new_chat_button.clicked.connect(self.new_chat)
            top_bar_layout.addWidget(self.new_chat_button)

            self.systemMessageLabel = QLabel()  # Add this line
            self.systemMessageLabel.setFont(QFont('SF Pro Text', 10))
            self.systemMessageLabel.setStyleSheet("""
            QLabel {
                color: #555;
                font-style: italic;
                padding: 5px;
                border-radius: 5px;
                background-color: #f0f0f0;
            }
            """)
            top_bar_layout.addWidget(self.systemMessageLabel)  # Add this line
            top_bar_layout.addStretch(1) # Add a stretch to push the label to the left

            main_layout.addLayout(top_bar_layout)
            
            # Create menu bar
            menubar = self.menuBar()
            self.menuBar().setStyleSheet("""
                QMenuBar {
                    background-color: #34495e;
                    color: white;
                    padding: 5px;
                }
                QMenuBar::item {
                    padding: 5px 10px;
                    background-color: transparent;
                }
                QMenuBar::item:selected {
                    background-color: #2c3e50;
                }
                QMenuBar::item:pressed {
                    background-color: #2980b9;
                }
            """)
            # Style for the menus
            self.setStyleSheet("""
                QMenu {
                    background-color: #34495e;
                    color: white;
                }
                QMenu::item {
                    padding: 5px 30px 5px 20px;
                }
                QMenu::item:selected {
                    background-color: #2980b9;
                }
            """)
            # File menu
            file_menu = menubar.addMenu('File')
            
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
            self.chat_area.setStyleSheet("""
            QScrollArea {
                border-radius: 10px;
                background-color: #f9f9f9;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #888;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            """)
            self.chat_area.setWidgetResizable(True)
            self.chat_content = QWidget()
            self.chat_layout = QVBoxLayout(self.chat_content)
            self.chat_layout.setAlignment(Qt.AlignTop)
            self.chat_area.setWidget(self.chat_content)
            main_layout.addWidget(self.chat_area)
            
            input_layout = QHBoxLayout()
            
            self.inputField = CustomTextEdit(self, chat_app=self)  # Pass the chat_app reference
            # Enhanced style for the input field
            self.inputField.setStyleSheet("""
                QLineEdit {
                    border-radius: 10px;
                    padding: 5px 10px;
                    background-color: #ecf0f1;
                    color: #2c3e50;
                    font-size: 14px;
                }
                QLineEdit:focus {
                    background-color: #fff;
                }
            """)
            self.inputField.setPlaceholderText("Type your message here...")
            self.inputField.setFont(QFont('SF Pro Text', 12))
            input_layout.addWidget(self.inputField)
            
            self.sendButton = QPushButton('Send')
            self.sendButton.setFont(QFont('SF Pro Text', 12))
            # Enhanced style for the send button
            self.sendButton.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 10px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:pressed {
                    background-color: #2573a7;
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
            
        except Exception as e:
            logging.error(f"Error in initUI: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to initialize the user interface: {str(e)}")

    def center(self):
        try:
            qr = self.frameGeometry()
            cp = QDesktopWidget().availableGeometry().center()
            qr.moveCenter(cp)
            self.move(qr.topLeft())
        except Exception as e:
            logging.error(f"Error centering window: {str(e)}")

    def add_system_message(self, message):
        try:
            self.systemMessageLabel.setText(message)
        except Exception as e:
            logging.error(f"Error adding system message: {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to add system message: {str(e)}")

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
        try:
            ollama_path = self.find_ollama_executable()

            if not ollama_path:
                QMessageBox.critical(self, "Error", "Ollama executable not found. Please ensure Ollama is installed and added to your system's PATH.")
                return

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
        try:
            ollama_path = self.find_ollama_executable()

            if not ollama_path:
                QMessageBox.critical(self, "Error", "Ollama executable not found. Please ensure Ollama is installed and added to your system's PATH.")
                return

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
        try:
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
        except Exception as e:
            logging.error(f"Error finding Ollama executable: {str(e)}")
            return None
    def update_chat_display(self, token: str):
        try:
            if self.current_ai_message:
                current_text = self.current_ai_message.text.toPlainText()
                self.current_ai_message.text.setPlainText(current_text + token)
                
                # Move cursor to the end
                cursor = self.current_ai_message.text.textCursor()
                cursor.movePosition(QTextCursor.End)
                self.current_ai_message.text.setTextCursor(cursor)
                
                # Adjust the size of the text area
                self.current_ai_message.adjust_size()
                
                # Scroll to the bottom
                self.chat_area.verticalScrollBar().setValue(self.chat_area.verticalScrollBar().maximum())
        except Exception as e:
            logging.error(f"Error updating chat display: {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to update chat display: {str(e)}")



    def add_message(self, message, is_user=True, message_id=None):
        try:
            msg_widget = MessageWidget(message, is_user, chat_app=self, message_id=message_id)
            
            # Create a QHBoxLayout to hold the message widget
            hbox = QHBoxLayout()
            hbox.setContentsMargins(0, 0, 0, 0)  # Remove margins around the message
            
            if is_user:
                hbox.addStretch()  # Add stretch before the widget to push it to the right
                hbox.addWidget(msg_widget)
            else:
                hbox.addWidget(msg_widget)
                hbox.addStretch()  # Add stretch after the widget to keep it on the left
            
            # Create a QWidget to hold the layout
            container = QWidget()
            container.setLayout(hbox)
            
            # Set the container height based on the text size
            container.setMinimumHeight(msg_widget.sizeHint().height())
            container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
            
            # Add the container to the chat layout
            self.chat_layout.addWidget(container)

            # Store the message in memory with the unique ID
            if is_user:
                new_message = HumanMessage(content=message)
            else:
                new_message = AIMessage(content=message)
            new_message.id = msg_widget.message_id
            self.memory.chat_memory.add_message(new_message)

            # Scroll to the bottom
            self.chat_area.verticalScrollBar().setValue(self.chat_area.verticalScrollBar().maximum())

            # Adjust font size
            msg_widget.text.setStyleSheet(f"font-size: {SETTINGS['font_size']}px;")

            # Update the system message
            self.add_system_message(f"Message added successfully. Using model: {SETTINGS['model']}")

        except Exception as e:
            logging.error(f"Error adding message: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to add message: {str(e)}")


    def update_message(self, message_id, new_content):
        try:
            # Find the message in the UI and update it
            for i in range(self.chat_layout.count()):
                widget = self.chat_layout.itemAt(i).widget()
                if isinstance(widget, MessageWidget) and widget.message_id == message_id:
                    widget.text.setMarkdown(new_content)
                    break
            
            # Update the message in memory
            self.memory.edit_message(message_id, new_content)
            
            self.add_system_message("Message updated successfully.")
        except Exception as e:
            logging.error(f"Error updating message: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to update message: {str(e)}")


    def sendMessage(self):
        try:
            userMessage = self.inputField.toMarkdown().strip()
            if not userMessage:
                return

            # Add user message with a unique ID
            user_message_id = uuid.uuid4().hex
            self.add_message(userMessage, is_user=True, message_id=user_message_id)
            self.inputField.clear()

            if self.llm is None:
                QMessageBox.warning(self, "Warning", "Model not loaded. Please check your settings and try again.")
                return

            self.memory.chat_memory.add_user_message(userMessage)
            messages = self.prompt_template.format_messages(input=userMessage, output="")
            messages.extend(self.memory.chat_memory.messages)
            self.chat_thread = ChatThread(self.llm, messages)
            self.chat_thread.response_ready.connect(self.handleResponse)
            self.chat_thread.error_occurred.connect(self.handleError)
            self.chat_thread.start()

            # Create a placeholder for AI message with a unique ID
            ai_message_id = uuid.uuid4().hex
            self.current_ai_message = MessageWidget("", is_user=False, chat_app=self, message_id=ai_message_id)
            self.chat_layout.addWidget(self.current_ai_message)
        except Exception as e:
            logging.error(f"Error sending message: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to send message: {str(e)}")

    def handleResponse(self, response):
        try:
            if self.current_ai_message:
                self.current_ai_message.text.setMarkdown(response)  # Update with Markdown
                self.memory.chat_memory.add_ai_message(response)
                self.current_ai_message = None
                self.chat_area.verticalScrollBar().setValue(self.chat_area.verticalScrollBar().maximum())
        except Exception as e:
            logging.error(f"Error handling response: {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to handle response: {str(e)}")


    def new_chat(self):
        try:
            self.memory = ConversationBufferMemory()
            self.clear_chat()
            self.add_system_message("New chat started")
        except Exception as e:
            logging.error(f"Error starting new chat: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to start new chat: {str(e)}")

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
                QApplication.clipboard().setText(last_message.text.toMarkdown())
                self.add_system_message("Last message copied to clipboard")
            else:
                QMessageBox.warning(self, "Warning", "No messages to copy")
        except Exception as e:
            logging.error(f"Error copying last message: {str(e)}")
            QMessageBox.warning(self, "Warning", f"Failed to copy last message: {str(e)}")

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
            gpus = GPUtil.getGPUs()
            gpu_info = ""
            total_gpu_vram = 0
            if gpus:
                for gpu in gpus:
                    gpu_info += f"<li>Name: {gpu.name}</li>"
                    gpu_info += f"<li>VRAM: {gpu.memoryTotal:.2f} GB</li>"
                    total_gpu_vram += gpu.memoryTotal
            else:
                # Check for AMD GPUs using wmi
                c = wmi.WMI()
                amd_gpus = c.Win32_VideoController(AdapterCompatibility="Advanced Micro Devices, Inc.")
                if amd_gpus:
                    for gpu in amd_gpus:
                        gpu_info += f"<li>Name: {gpu.Name}</li>"
                        vram = int(gpu.AdapterRAM) / (1024**3)  # Convert to GB
                        gpu_info += f"<li>VRAM: {vram:.2f} GB</li>"
                        total_gpu_vram += vram
                else:
                    gpu_info = "<li>No GPU detected.</li>"

            quantization_bits = 4  # Fixed for this implementation
            overhead_factor = 1.5   # Overhead factor for additional memory usage

            # Calculate the maximum number of parameters that can fit in the GPU memory
            max_memory_for_parameters_gb = total_gpu_vram / overhead_factor
            max_llm_size_billion = round(max_memory_for_parameters_gb / (quantization_bits / 8) /1000)
            html_message = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f0f4f8; color: #333; }}
                    .container {{ max-width: 800px; margin: 0 auto; padding: 20px; background-color: white; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                    h1 {{ color: #2ecc71; font-size: 3.5em; text-align: center; margin-bottom: 10px; }}
                    h2 {{ color: #3498db; text-align: center; margin-top: 0; }}
                    .info {{ margin-top: 20px; }}
                    .info h3 {{ color: #e67e22; }}
                    .info p {{ line-height: 1.6; }}
                    ul {{ list-style-type: none; padding-left: 0; }}
                    li {{ margin-bottom: 10px; }}
                    .note {{ background-color: #fef9e7; border-left: 5px solid #f39c12; padding: 10px; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>Your System's AI Potential</h2>
                    <h1>🚀 {max_llm_size_billion}B</h1>
                    <div class="info">
                        <h3>📊 What This Means For You</h3>
                        <p>Great news! Your computer can handle AI models with up to {max_llm_size_billion} billion parameters. That's impressive!</p>
                        <h3>💻 Your GPU Details</h3>
                        <ul>
                            {gpu_info}
                        </ul>
                        <div class="note">
                            <p><strong>Quick Tip:</strong> We've factored in some extra headroom to ensure smooth performance. The actual capability might vary slightly based on your specific setup and usage.</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """

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
                    "messages": [
                        {
                            "type": msg.type, 
                            "content": msg.content,
                            "id": getattr(msg, 'id', None)  # Include the message ID
                        } 
                        for msg in self.memory.chat_memory.messages
                    ],
                    "model": self.llm.model if self.llm else SETTINGS['model']  # Use current model or default
                }
                with open(file_name, 'w') as f:
                    json.dump(chat_data, f, indent=4)
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
                # Clear existing memory and UI
                self.memory = ConversationBufferMemory()
                self.clear_chat()
                # Load messages with IDs
                for msg in chat_data.get("messages", []):
                    msg_type = msg.get("type")
                    content = msg.get("content")
                    msg_id = msg.get("id")
                    if msg_type and content:
                        self.add_message(content, is_user=(msg_type == "human"), message_id=msg_id)
                # Set model
                model = chat_data.get("model", SETTINGS['model'])
                self.llm = ChatOllama(
                    model=model,
                    streaming=True,
                    callbacks=[self.stream_handler],
                )
                self.add_system_message(f"Chat loaded from {file_name} with model {model}")
        except Exception as e:
            logging.error(f"Error loading chat: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load chat: {str(e)}")

    def validate_message_ids(self):
        memory_ids = set(msg.id for msg in self.memory.chat_memory.messages)
        ui_ids = set()
        for i in range(self.chat_layout.count()):
            widget = self.chat_layout.itemAt(i).widget()
            if isinstance(widget, MessageWidget):
                ui_ids.add(widget.message_id)
        missing_in_memory = ui_ids - memory_ids
        missing_in_ui = memory_ids - ui_ids
        if missing_in_memory:
            logging.warning(f"Messages present in UI but missing in memory: {missing_in_memory}")
        if missing_in_ui:
            logging.warning(f"Messages present in memory but missing in UI: {missing_in_ui}")

    def toggle_dark_mode(self):
        if self.palette().color(QPalette.Window).lightness() > 128:
            # Dark mode
            self.setStyleSheet("""
                QWidget {
                    background-color: #2c3e50;
                    color: #ecf0f1;
                }
                QLineEdit, QTextEdit {
                    background-color: #34495e;
                    color: #ecf0f1;
                    border: none;
                    border-radius: 5px;
                    padding: 5px;
                }
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 15px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QScrollArea {
                    border: none;
                }
                QMenuBar {
                    background-color: #34495e;
                    color: #ecf0f1;
                }
                QMenuBar::item:selected {
                    background-color: #2980b9;
                }
                QMenu {
                    background-color: #34495e;
                    color: #ecf0f1;
                }
                QMenu::item:selected {
                    background-color: #2980b9;
                }
            """)
        else:
            self.toggle_light_mode()


    def toggle_light_mode(self):
        # Light mode
        self.setStyleSheet("""
                QWidget {
                    background-color: #ecf0f1;
                    color: #2c3e50;
                }
                QLineEdit, QTextEdit {
                    background-color: white;
                    color: #2c3e50;
                    border: none;
                    border-radius: 5px;
                    padding: 5px;
                }
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 15px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QScrollArea {
                    border: none;
                }
                QMenuBar {
                    background-color: #3498db;
                    color: white;
                }
                QMenuBar::item:selected {
                    background-color: #2980b9;
                }
                QMenu {
                    background-color: white;
                    color: #2c3e50;
                }
                QMenu::item:selected {
                    background-color: #3498db;
                    color: white;
                }
                """)
    def apply_system_theme(self):
        try:
            # Get the current system theme using the Windows registry
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            theme_mode, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)

            # Apply the appropriate theme based on the system setting
            if theme_mode == 0:  # Dark mode
                self.toggle_dark_mode()
            else:  # Light mode
                self.toggle_light_mode()

        except Exception as e:
            logging.error(f"Error applying system theme: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to apply system theme: {str(e)}")
    
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
            default_index = models.index(SETTINGS['model']) if SETTINGS['model'] in models else 0
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Change Model")
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #f0f0f0;
                    border-radius: 10px;
                }
                QComboBox {
                    background-color: white;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                    padding: 5px;
                    min-width: 200px;
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox::down-arrow {
                    image: url(down_arrow.png);
                    width: 14px;
                    height: 14px;
                }
                QCheckBox {
                    spacing: 5px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                }
                QLineEdit {
                    background-color: white;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                    padding: 5px;
                }
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 15px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
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
                    SETTINGS['model'] = model
                    save_settings(SETTINGS)
                    self.change_model()

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
    app.setStyle('Fusion')  # Set Fusion theme
    chatbot = ChatbotApp()
    chatbot.show()
    sys.exit(app.exec_())
