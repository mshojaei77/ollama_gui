# chatbot_app.py
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from PyQt5 import QtCore
from views.main_window_ui import Ui_MainWindow
from handlers.settings_handler import SettingsHandler, SETTINGS
from handlers.model_handler import ModelHandler
from handlers.memory_handler import MemoryHandler
from handlers.chat_handler import ChatHandler, StreamHandler
from handlers.ui_handler import UIHandler
from utility import Utility
from langchain.prompts import PromptTemplate
from logger import app_logger

class ChatbotApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.initialize_handlers()
        self.initialize_prompt_template()
        self.initUI()

    def initialize_handlers(self):
        try:
            self.stream_handler = StreamHandler()
            self.settings_handler = SettingsHandler(self)
            self.ui_handler = UIHandler(self)
            self.model_handler = ModelHandler(self)
            self.memory_handler = MemoryHandler(self)
            self.chat_handler = ChatHandler(self)
            app_logger.info("Handlers initialized successfully")
        except Exception as e:
            app_logger.error(f"Error initializing handlers: {str(e)}", exc_info=True)
            self.show_error_message("Failed to initialize handlers", str(e))

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
        self.ui.actionSaveChat.triggered.connect(self.chat_handler.save_chat)
        self.ui.actionLoadChat.triggered.connect(self.chat_handler.load_chat)
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