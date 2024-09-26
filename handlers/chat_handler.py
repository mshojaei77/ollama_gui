# chat_handler.py
import logging
import uuid
import json
import os
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QApplication
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QThread
from langchain.memory import ConversationBufferMemory
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import HumanMessage, AIMessage
from widgets.message_widget import MessageWidget
from logger import app_logger  # Import the logger
from handlers.database_handler import DatabaseHandler
from datetime import datetime

class StreamHandler(QObject, BaseCallbackHandler):
    new_token = pyqtSignal(str)

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        try:
            self.new_token.emit(token)
        except Exception as e:
            app_logger.error(f"Error in StreamHandler: {str(e)}")

class ChatThread(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, llm, messages):
        super().__init__()
        self.llm = llm
        self.messages = messages
    
    def run(self):
        try:
            os.environ['no_proxy'] = 'localhost,127.0.0.1'
            response = self.llm.invoke(self.messages)
            self.response_ready.emit(response.content)
        except Exception as e:
            app_logger.error(f"Error in ChatThread: {str(e)}")
            error_message = "Oops! We couldn't connect to Ollama on your computer. This might be because of a VPN or proxy. Please try turning off any VPN or proxy you're using, and then try again." if "503" in str(e) else str(e)
            self.error_occurred.emit(error_message)

class ChatHandler:
    def __init__(self, app):
        self.app = app
        self.chat_thread = None
        self.current_ai_message = None
        self.db_handler = DatabaseHandler()
        self.current_chat_id = None
        self.load_chat_list()

    def send_message(self):
        try:
            user_message = self.app.ui.inputField.toMarkdown().strip()
            if not user_message:
                return
            
            user_message_id = uuid.uuid4().hex
            self.app.ui_handler.add_message(user_message, is_user=True, message_id=user_message_id)
            self.app.ui.inputField.clear()
            
            if self.app.llm is None:
                QMessageBox.warning(self.app, "Warning", "Model not loaded. Please check your settings and try again.")
                return

            self.app.memory_handler.memory.chat_memory.add_user_message(user_message)
            
            formatted_prompt = self.app.prompt_template.format(input=user_message)
            messages = [HumanMessage(content=formatted_prompt)]
            messages.extend(self.app.memory_handler.memory.chat_memory.messages)
            
            self.chat_thread = ChatThread(self.app.llm, messages)
            self.chat_thread.response_ready.connect(self.handle_response)
            self.chat_thread.error_occurred.connect(self.handle_error)
            self.chat_thread.start()
            
            ai_message_id = uuid.uuid4().hex
            self.current_ai_message = MessageWidget("", is_user=False, chat_app=self.app, message_id=ai_message_id)
            self.app.ui.chatLayout.addWidget(self.current_ai_message)
        except Exception as e:
            app_logger.error(f"Error sending message: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to send message: {str(e)}")

    def handle_response(self, response):
        try:
            if self.current_ai_message:
                self.current_ai_message.text.setMarkdown(response)
                self.app.memory_handler.memory.chat_memory.add_ai_message(response)
                self.current_ai_message = None
                self.app.ui.chatScrollArea.verticalScrollBar().setValue(
                    self.app.ui.chatScrollArea.verticalScrollBar().maximum()
                )
                self.save_chat()
        except Exception as e:
            app_logger.error(f"Error handling response: {str(e)}")
            QMessageBox.warning(self.app, "Warning", f"Failed to handle response: {str(e)}")

    def handle_error(self, error_message):
        app_logger.error(f"Error in chat thread: {error_message}")
        try:
            if "404" in error_message and "pull the model" in error_message:
                model_name = error_message.split("`ollama pull ")[-1].split("`")[0]
                reply = QMessageBox.question(self.app, "Model Not Found", 
                                             f"The model {model_name} is not found. Do you want to pull it?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.Yes:
                    self.app.model_handler.pull_model(model_name)
            else:
                QMessageBox.critical(self.app, "Error", f"{error_message}")
        except Exception as e:
            app_logger.error(f"Error handling error message: {str(e)}")
            QMessageBox.critical(self.app, "Critical Error", f"Failed to handle error message: {str(e)}")

    def new_chat(self):
        try:
            self.app.memory_handler.memory = ConversationBufferMemory()
            self.clear_chat()
            self.current_chat_id = None
            self.app.ui_handler.add_system_message("New chat started")
            self.update_chat_list()
        except Exception as e:
            app_logger.error(f"Error starting new chat: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to start new chat: {str(e)}")

    def export_chat(self):
        try:
            file_name, _ = QFileDialog.getSaveFileName(self.app, "Export Chat", "", "Text Files (*.txt);;All Files (*)")
            if file_name:
                with open(file_name, 'w', encoding='utf-8') as file:
                    for message in self.app.memory_handler.memory.chat_memory.messages:
                        role = "User" if isinstance(message, HumanMessage) else "AI"
                        file.write(f"{role}: {message.content}\n")
                self.app.ui_handler.add_system_message("Chat exported successfully.")
        except Exception as e:
            app_logger.error(f"Error exporting chat: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to export chat: {str(e)}")

    def save_chat(self):
        try:
            if not self.app.memory_handler.memory.chat_memory.messages:
                return
            
            title = self.app.memory_handler.memory.chat_memory.messages[0].content[:50]  # Use first message as title
            messages = self.app.memory_handler.memory.chat_memory.messages
            
            if self.current_chat_id:
                self.db_handler.delete_chat(self.current_chat_id)
            
            self.current_chat_id = self.db_handler.save_chat(title, messages)
            self.update_chat_list()
            self.app.ui_handler.add_system_message("Chat saved successfully.")
        except Exception as e:
            app_logger.error(f"Error saving chat: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to save chat: {str(e)}")

    def load_chat(self, chat_id):
        try:
            title, messages = self.db_handler.load_chat(chat_id)
            self.app.memory_handler.memory.chat_memory.messages = messages
            self.clear_chat()
            for message in messages:
                self.app.ui_handler.add_message(message.content, isinstance(message, HumanMessage))
            self.current_chat_id = chat_id
            self.app.ui_handler.add_system_message(f"Chat '{title}' loaded successfully.")
            self.app.ui.chatListWidget.setCurrentRow(self.get_chat_list_index(chat_id))
        except Exception as e:
            app_logger.error(f"Error loading chat: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to load chat: {str(e)}")

    def load_chat_list(self):
        try:
            chat_list = self.db_handler.get_chat_list()
            self.app.ui.chatListWidget.clear()
            for chat in chat_list:
                item = QtWidgets.QListWidgetItem(f"{chat[1]} - {chat[2]}")
                item.setData(Qt.UserRole, chat[0])
                self.app.ui.chatListWidget.addItem(item)
        except Exception as e:
            app_logger.error(f"Error loading chat list: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to load chat list: {str(e)}")

    def update_chat_list(self):
        self.load_chat_list()

    def search_chats(self, query):
        try:
            search_results = self.db_handler.search_chats(query)
            self.app.ui.chatListWidget.clear()
            for chat in search_results:
                item = QtWidgets.QListWidgetItem(f"{chat[1]} - {chat[2]}")
                item.setData(Qt.UserRole, chat[0])
                self.app.ui.chatListWidget.addItem(item)
        except Exception as e:
            app_logger.error(f"Error searching chats: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to search chats: {str(e)}")

    def delete_chat(self):
        try:
            current_item = self.app.ui.chatListWidget.currentItem()
            if current_item:
                chat_id = current_item.data(Qt.UserRole)
                reply = QMessageBox.question(self.app, 'Delete Chat', 
                                             'Are you sure you want to delete this chat?',
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.db_handler.delete_chat(chat_id)
                    self.update_chat_list()
                    if self.current_chat_id == chat_id:
                        self.new_chat()
                    self.app.ui_handler.add_system_message("Chat deleted successfully.")
            else:
                QMessageBox.warning(self.app, "Warning", "No chat selected for deletion.")
        except Exception as e:
            app_logger.error(f"Error deleting chat: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to delete chat: {str(e)}")

    def get_chat_list_index(self, chat_id):
        for i in range(self.app.ui.chatListWidget.count()):
            if self.app.ui.chatListWidget.item(i).data(Qt.UserRole) == chat_id:
                return i
        return -1

    def clear_chat(self):
        try:
            while self.app.ui.chatLayout.count():
                item = self.app.ui.chatLayout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            self.app.memory_handler.memory.chat_memory.clear()
            self.app.ui_handler.add_system_message("Chat cleared.")
        except Exception as e:
            app_logger.error(f"Error clearing chat: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to clear chat: {str(e)}")

    def copy_last_message(self):
        try:
            if self.app.memory_handler.memory.chat_memory.messages:
                last_message = self.app.memory_handler.memory.chat_memory.messages[-1]
                clipboard = QApplication.clipboard()
                clipboard.setText(last_message.content)
                self.app.ui_handler.add_system_message("Last message copied to clipboard.")
        except Exception as e:
            app_logger.error(f"Error copying last message: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to copy last message: {str(e)}")