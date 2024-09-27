# main.py
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from handlers.settings_handler import SettingsHandler
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QEvent
from views.main_window_ui import Ui_MainWindow
from handlers.settings_handler import SettingsHandler
from handlers.model_handler import ModelHandler
from handlers.memory_handler import MemoryHandler
from handlers.chat_handler import ChatHandler, StreamHandler
from handlers.ui_handler import UIHandler
from utility import Utility
from langchain.prompts import PromptTemplate
from logger import app_logger
import os
import subprocess
from PyQt5.QtGui import QIcon

if sys.platform.startswith('win'):
    try:
        subprocess.Popen(['powershell', '-Command', 'ollama list'], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        app_logger.error(f"Failed to start Ollama: {str(e)}")
        QMessageBox.warning(None, "Warning", f"Failed to start Ollama: {str(e)}\nPlease ensure Ollama is installed and accessible from PowerShell.")

class ChatbotApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.initialize_handlers()
        self.initialize_prompt_template()
        self.initUI()
        self.set_app_icon()  # Add this line

    def initialize_handlers(self):
        try:
            self.settings_handler = SettingsHandler(self)
            self.ui_handler = UIHandler(self)
            self.chat_handler = ChatHandler(self)  # Move this up
            self.model_handler = ModelHandler(self)
            self.memory_handler = MemoryHandler(self)
            self.setup_input_field()
            app_logger.info("Handlers initialized successfully")
        except Exception as e:
            app_logger.error(f"Error initializing handlers: {str(e)}", exc_info=True)
            self.show_error_message("Failed to initialize handlers", str(e))

    def setup_input_field(self):
        self.ui.inputField.installEventFilter(self)
        self.ui.inputField.setAcceptRichText(False)

    def eventFilter(self, obj, event):
        if obj == self.ui.inputField and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() & Qt.ShiftModifier:
                    # Shift+Enter: insert a new line
                    cursor = self.ui.inputField.textCursor()
                    cursor.insertText('\n')
                else:
                    # Enter without Shift: send the message
                    self.chat_handler.send_message()
                return True
        return super().eventFilter(obj, event)

    def initialize_prompt_template(self):
        try:
            self.prompt_template = PromptTemplate(
                input_variables=["input"],
                template="You are a helpful AI assistant. {input}"
            )
            app_logger.info("Prompt template initialized")
        except Exception as e:
            app_logger.error(f"Error initializing prompt template: {str(e)}", exc_info=True)
            self.show_error_message("Failed to initialize prompt template", str(e))

    def initUI(self):
        try:
            # Set window properties
            self.setWindowTitle('Ollama Chatbot v0.3')
            self.resize(1000, 900)
            self.ui_handler.center()

            # Connect UI elements to their respective handlers
            self.connect_ui_elements()

            # Initialize the model
            self.model_handler.change_model()

            app_logger.info("UI initialized successfully")
        except Exception as e:
            app_logger.error(f"Error in initUI: {str(e)}", exc_info=True)
            self.show_error_message("Failed to initialize the user interface", str(e))

    def connect_ui_elements(self):
        # Connect buttons
        self.ui.newChatButton.clicked.connect(self.chat_handler.new_chat)
        self.ui.sendButton.clicked.connect(self.chat_handler.send_message)

        # Connect menu actions
        self.ui.actionClear_Chat_History.triggered.connect(self.chat_handler.clear_chat_list)
        self.ui.actionExportChat.triggered.connect(self.chat_handler.export_chat)
        self.ui.actionClearChat.triggered.connect(self.chat_handler.clear_chat)
        self.ui.actionCopyLastMessage.triggered.connect(self.chat_handler.copy_last_message)
        self.ui.actionToggleDarkMode.triggered.connect(self.settings_handler.toggle_dark_mode)
        self.ui.actionChangeModel.triggered.connect(self.model_handler.change_model_dialog)
        self.ui.actionShowAvailableModels.triggered.connect(self.model_handler.list_models)
        self.ui.actionOpenSettings.triggered.connect(self.settings_handler.open_settings)
        self.ui.actionShowSystemInfo.triggered.connect(self.ui_handler.show_system_info)
        self.ui.actionAbout.triggered.connect(self.ui_handler.show_about)

        # Connect chat list and search functionality
        self.ui.chatListWidget.itemClicked.connect(self.load_selected_chat)
        self.ui.searchLineEdit.returnPressed.connect(self.search_chats)

    def show_error_message(self, title, message):
        QMessageBox.critical(self, title, message)

    def load_selected_chat(self, item):
        chat_id = item.data(QtCore.Qt.UserRole)
        self.chat_handler.load_chat(chat_id)

    def search_chats(self):
        query = self.ui.searchLineEdit.text()
        self.chat_handler.search_chats(query)

    def set_app_icon(self):
        icon_path = os.path.join('assets', 'ollama.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            app_logger.warning(f"Icon file not found: {icon_path}")

def initialize_app():
    """Initialize and run the ChatbotApp."""
    try:
        app = QApplication(sys.argv)
        app_logger.info("QApplication initialized")
        
        settings_handler = SettingsHandler(app)
        settings_handler.load_stylesheet()
        app_logger.info("Stylesheet loaded")
        
        window = ChatbotApp()
        app_logger.info("ChatbotApp instance created")
        
        # Set window size
        window.resize(1200, 850)  
        
        # Center the window
        screen = app.primaryScreen().geometry()
        x = (screen.width() - window.width()) // 2
        y = (screen.height() - window.height()) // 2
        window.move(x, y)
        
        # Show the main window
        window.show()
        app_logger.info("ChatbotApp window shown and centered")
        
        return app.exec_()
    except Exception as e:
        app_logger.error(f"Error initializing app: {str(e)}", exc_info=True)
        # Display error message box
        QMessageBox.critical(None, "Critical Error", f"An error occurred while initializing the application: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(initialize_app())