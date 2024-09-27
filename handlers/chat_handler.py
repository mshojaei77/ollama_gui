# chat_handler.py
import logging
import uuid
import os
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QApplication
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QThread, QEvent
from langchain.memory import ConversationBufferMemory
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import HumanMessage, AIMessage
from widgets.message_widget import MessageWidget
from logger import app_logger
from handlers.database_handler import DatabaseHandler

# Stream Handler for real-time token processing
class StreamHandler(QObject, BaseCallbackHandler):
    new_token = pyqtSignal(str)

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        try:
            self.new_token.emit(token)
        except Exception as e:
            app_logger.error(f"Error in StreamHandler: {str(e)}")

# Thread for handling chat operations
class ChatThread(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    token_ready = pyqtSignal(str)  # New signal for token updates
    
    def __init__(self, app, llm, messages):
        super().__init__()
        self.app = app
        self.llm = llm
        self.messages = messages
        self.stream_handler = StreamHandler()
        self.stream_handler.new_token.connect(self.on_new_token)
    
    def run(self):
        try:
            os.environ['no_proxy'] = 'localhost,127.0.0.1'
            response = self.llm.invoke(self.messages)
            self.response_ready.emit(response.content)
        except Exception as e:
            app_logger.error(f"Error in ChatThread: {str(e)}")
            error_message = "Oops! We couldn't connect to Ollama on your computer. This might be because of a VPN or proxy. Please try turning off any VPN or proxy you're using, and then try again." if "503" in str(e) else str(e)
            self.error_occurred.emit(error_message)

    def on_new_token(self, token: str):
        self.token_ready.emit(token)

# Main Chat Handler
class ChatHandler(QObject):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.chat_thread = None
        self.current_ai_message = None
        self.db_handler = DatabaseHandler()
        self.current_chat_id = None
        self.chat_widget = None
        self.chat_layout = None
        self.stream_handler = StreamHandler()
        self.stream_handler.new_token.connect(self.update_ai_message)
        
        # Initialize UI components
        self.load_chat_list()
        self.setup_chat_area()
        self.setup_input_field()

    # UI Setup Methods
    def setup_chat_area(self):
        """Set up the main chat area widget and layout"""
        self.chat_widget = QtWidgets.QWidget()
        self.chat_layout = QtWidgets.QVBoxLayout(self.chat_widget)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(10)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        
        self.app.ui.chatScrollArea.setWidget(self.chat_widget)
        self.app.ui.chatScrollArea.setWidgetResizable(True)

    def setup_input_field(self):
        """Configure the input field for message entry"""
        self.app.ui.inputField.setAcceptRichText(False)

    # Message Handling Methods
    def send_message(self):
        """Process and send user message, initiate AI response"""
        try:
            user_message = self.app.ui.inputField.toMarkdown().strip()
            if not user_message:
                return
            
            # Add user message to UI and memory
            user_message_id = uuid.uuid4().hex
            self.app.ui_handler.add_message(user_message, is_user=True, message_id=user_message_id)
            self.app.ui.inputField.clear()
            
            if self.app.llm is None:
                QMessageBox.warning(self.app, "Warning", "Model not loaded. Please check your settings and try again.")
                return

            self.app.memory_handler.memory.chat_memory.add_user_message(user_message)
            
            # Prepare and send message to AI
            formatted_prompt = self.app.prompt_template.format(input=user_message)
            messages = [HumanMessage(content=formatted_prompt)]
            messages.extend(self.app.memory_handler.memory.chat_memory.messages)
            
            self.chat_thread = ChatThread(self.app, self.app.llm, messages)
            self.chat_thread.response_ready.connect(self.handle_response)
            self.chat_thread.error_occurred.connect(self.handle_error)
            self.chat_thread.token_ready.connect(self.update_ai_message)  # Connect to the new signal
            self.chat_thread.start()
            
            # Prepare UI for AI response
            ai_message_id = uuid.uuid4().hex
            self.current_ai_message = MessageWidget("", is_user=False, chat_app=self.app, message_id=ai_message_id)
            self.add_message_widget(self.current_ai_message)
            self.scroll_to_bottom()
        except Exception as e:
            app_logger.error(f"Error sending message: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to send message: {str(e)}")

    def update_ai_message(self, token):
        if self.current_ai_message:
            current_text = self.current_ai_message.text.toPlainText()
            self.current_ai_message.text.setPlainText(current_text + token)
            self.scroll_to_bottom()

    def add_message_widget(self, message_widget):
        """Add a message widget to the chat layout"""
        if self.chat_layout is not None:
            self.chat_layout.addWidget(message_widget)
        else:
            app_logger.error("Chat layout is not initialized")

    def handle_response(self, response):
        """Process and display AI response"""
        try:
            if self.current_ai_message:
                # Final update to ensure complete message
                self.current_ai_message.text.setPlainText(response)
                self.app.memory_handler.memory.chat_memory.add_ai_message(response)
                self.current_ai_message = None
                self.scroll_to_bottom()
                self.save_chat()
        except Exception as e:
            app_logger.error(f"Error handling response: {str(e)}")
            QMessageBox.warning(self.app, "Warning", f"Failed to handle response: {str(e)}")

    def handle_error(self, error_message):
        """Handle and display error messages"""
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

    # Chat Management Methods
    def new_chat(self):
        """Start a new chat session"""
        try:
            self.app.memory_handler.memory = ConversationBufferMemory()
            self.clear_chat()
            self.current_chat_id = None
            self.app.ui_handler.add_system_message("Great! A new chat has been started. You can now begin your conversation.")
            self.update_chat_list()
        except Exception as e:
            app_logger.error(f"Error starting new chat: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to start new chat: {str(e)}")

    def export_chat(self):
        """Export current chat to a file"""
        try:
            file_name, _ = QFileDialog.getSaveFileName(self.app, "Export Chat", "", "Text Files (*.txt);;All Files (*)")
            if file_name:
                with open(file_name, 'w', encoding='utf-8') as file:
                    for message in self.app.memory_handler.memory.chat_memory.messages:
                        role = "User" if isinstance(message, HumanMessage) else "AI"
                        file.write(f"{role}: {message.content}\n")
                self.app.ui_handler.add_system_message("Your chat has been successfully exported to a file. You can find it in the location you selected.")
        except Exception as e:
            app_logger.error(f"Error exporting chat: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to export chat: {str(e)}")

    def save_chat(self):
        """Save current chat to database"""
        try:
            if not self.app.memory_handler.memory.chat_memory.messages:
                return
            
            title = self.app.memory_handler.memory.chat_memory.messages[0].content[:50]  # Use first message as title
            messages = self.app.memory_handler.memory.chat_memory.messages
            
            if self.current_chat_id:
                self.db_handler.delete_chat(self.current_chat_id)
            
            self.current_chat_id = self.db_handler.save_chat(title, messages)
            self.update_chat_list()
            self.app.ui_handler.add_system_message("Your chat has been saved successfully. You can access it later from the chat list.")
        except Exception as e:
            app_logger.error(f"Error saving chat: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to save chat: {str(e)}")

    def load_chat(self, chat_id):
        """Load a chat from database"""
        try:
            title, messages = self.db_handler.load_chat(chat_id)
            
            # Clear existing chat from UI and memory
            self.clear_chat()
            
            # Add each message to the UI and memory only once
            seen_messages = set()
            for message in messages:
                if message.content not in seen_messages:
                    is_user = isinstance(message, HumanMessage)
                    self.app.ui_handler.add_message(message.content, is_user=is_user, add_to_memory=True)
                    seen_messages.add(message.content)
            
            self.current_chat_id = chat_id
            self.app.ui_handler.add_system_message(f"The chat '{title}' has been loaded successfully. You can now continue your conversation from where you left off.")
            self.app.ui.chatListWidget.setCurrentRow(self.get_chat_list_index(chat_id))
        except Exception as e:
            app_logger.error(f"Error loading chat: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to load chat: {str(e)}")

    # Chat List Management Methods
    def load_chat_list(self):
        try:
            chat_list = self.db_handler.get_chat_list()
            
            self.app.ui.chatListWidget.clear()
            
            for chat in chat_list:
                chat_id, content, _ = chat
                summary = self.generate_three_word_summary(content)
                item = QtWidgets.QListWidgetItem(summary)
                item.setData(Qt.UserRole, chat_id)
                self.app.ui.chatListWidget.addItem(item)
        except Exception as e:
            app_logger.error(f"Error loading chat list: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to load chat list: {str(e)}")
    def generate_three_word_summary(self, text):
        try:
            # Split the text into words
            words = text.split()
            
            # Count the occurrences of each word
            word_counts = {}
            for word in words:
                word = word.lower()  # Convert to lowercase for case-insensitive counting
                if word.isalnum():  # Only count alphanumeric words
                    word_counts[word] = word_counts.get(word, 0) + 1
            
            # Sort words by their count, then alphabetically
            sorted_words = sorted(word_counts.items(), key=lambda x: (-x[1], x[0]))
            
            # Select top 3 words
            top_three = [word for word, count in sorted_words[:3]]
            
            # Join the top three words
            summary = " ".join(top_three)
            
            return summary[:30]  # Limit to 30 characters
        except Exception as e:
            app_logger.error(f"Error generating summary: {str(e)}")
            return text[:30] + "..."  # Fallback to original method if error occurs

    def update_chat_list(self):
        """Update the displayed chat list"""
        self.load_chat_list()

    def clear_chat_list(self):
        """Clear the displayed chat list and delete all chats from the database"""
        try:
            reply = QMessageBox.question(self.app, 'Clear All Chats', 
                                        'Are you sure you want to delete all chats? This action cannot be undone.',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.app.ui.chatListWidget.clear()
                self.db_handler.clear_all_chats()
                self.current_chat_id = None
                self.new_chat()
                self.app.ui_handler.add_system_message("All your previous chats have been deleted. You're starting with a clean slate!")
        except Exception as e:
            app_logger.error(f"Error clearing chat list: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to clear chat list: {str(e)}")

    def search_chats(self, query):
        """Search and display chats matching the query"""
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
        """Delete the selected chat"""
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
                    self.app.ui_handler.add_system_message("The selected chat has been deleted successfully. You can start a new conversation or select another chat from the list.")
            else:
                QMessageBox.warning(self.app, "Warning", "No chat selected for deletion.")
        except Exception as e:
            app_logger.error(f"Error deleting chat: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to delete chat: {str(e)}")

    def get_chat_list_index(self, chat_id):
        """Get the index of a chat in the chat list"""
        for i in range(self.app.ui.chatListWidget.count()):
            if self.app.ui.chatListWidget.item(i).data(Qt.UserRole) == chat_id:
                return i
        return -1

    # Utility Methods
    def clear_chat(self):
        """Clear the current chat from UI and memory"""
        try:
            if self.chat_layout is not None:
                while self.chat_layout.count():
                    item = self.chat_layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
            self.app.memory_handler.memory.chat_memory.clear()
            self.app.ui_handler.add_system_message("The chat has been cleared. You can start a fresh conversation now!")
        except Exception as e:
            app_logger.error(f"Error clearing chat: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to clear chat: {str(e)}")

    def copy_last_message(self):
        """Copy the last message to clipboard"""
        try:
            if self.app.memory_handler.memory.chat_memory.messages:
                last_message = self.app.memory_handler.memory.chat_memory.messages[-1]
                clipboard = QApplication.clipboard()
                clipboard.setText(last_message.content)
                self.app.ui_handler.add_system_message("The last message has been copied to your clipboard. You can now paste it anywhere you like!")
        except Exception as e:
            app_logger.error(f"Error copying last message: {str(e)}")
            QMessageBox.critical(self.app, "Error", f"Failed to copy last message: {str(e)}")

    def scroll_to_bottom(self):
        """Scroll the chat area to the bottom"""
        QApplication.processEvents()
        self.app.ui.chatScrollArea.verticalScrollBar().setValue(
            self.app.ui.chatScrollArea.verticalScrollBar().maximum()
        )