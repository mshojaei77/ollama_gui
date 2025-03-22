import logging
import uuid
import mistune
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QTextEdit, QPushButton, QSizePolicy, QMessageBox, QFrame, QInputDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from logger import app_logger  # Importing the logger
import os

class MessageWidget(QWidget):
    def __init__(self, message, is_user, chat_app=None, message_id=None):
        super().__init__()
        self.chat_app = chat_app
        self.message_id = message_id if message_id else uuid.uuid4().hex
        self.is_user = is_user
        self.is_editing = False

        self.init_ui(message)

    def init_ui(self, message):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)

        self.create_text_edit(message)
        self.create_edit_button()

        text_container = QHBoxLayout()
        self.arrange_ui_elements(text_container)

        layout.addLayout(text_container)

        self.setLayout(layout)
        self.setContentsMargins(0, 5, 0, 5)

        # Initial size adjustment
        self.adjust_size()

    def create_text_edit(self, message):
        # $ Text Edit UI Element
        self.text = QTextEdit()
        
        # Convert markdown to HTML using mistune
        markdown_parser = mistune.create_markdown()
        html_content = markdown_parser(message)
        self.text.setHtml(html_content)
        
        self.text.setReadOnly(True)
        self.text.setFont(QFont('SF Pro Text', 13))
        
        # Disable scrollbars completely
        self.text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.text.setFrameStyle(QFrame.NoFrame)
        
        # Allow the widget to expand in both directions
        self.text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Make sure size is adjusted whenever content changes
        self.text.document().contentsChanged.connect(self.adjust_size)

        # Set object name for styling
        self.text.setObjectName("messageText")
        self.text.setProperty("is_user", str(self.is_user).lower())

    def create_edit_button(self):
        # $ Edit Button UI Element
        self.edit_button = QPushButton()
        self.edit_button.setIcon(QIcon(os.path.join('assets', 'pencil-50.svg')))
        self.edit_button.setToolTip("Edit message")
        self.edit_button.setFixedSize(24, 24)
        self.edit_button.setStyleSheet("background-color: transparent; border: none;")
        self.edit_button.clicked.connect(self.edit_message)
        
        # Set object name for styling
        self.edit_button.setObjectName("editButton")

    def arrange_ui_elements(self, container):
        if self.is_user:
            container.addStretch()
            container.addWidget(self.edit_button)
            container.addWidget(self.text)
        else:
            container.addWidget(self.text)
            container.addWidget(self.edit_button)
            container.addStretch()

    def adjust_size(self):
        try:
            doc = self.text.document()
            doc.setTextWidth(self.text.viewport().width())
            doc_height = doc.size().height()
            
            max_width = min(int(self.chat_app.width() * 0.9) if self.chat_app else 900, 900)
            min_width = max(int(self.chat_app.width() * 0.2) if self.chat_app else 300, 300)
            
            new_width = max(min(int(doc.idealWidth()) + 50, max_width), min_width)
            
            # Calculate height with extra padding to ensure all content is visible
            # Using a smaller fixed padding (30 instead of 80) and letting the document size determine more of the height
            new_height = int(doc_height) + 30
            
            self.text.setMinimumWidth(min_width)
            self.text.setMaximumWidth(max_width)
            
            # Set the height to accommodate all content
            self.text.setMinimumHeight(new_height)
            self.text.setMaximumHeight(new_height)  # Set maximum height to match minimum
            
            # Update the widget's height as well
            self.setMinimumHeight(new_height + 10)  # Reduced padding from 20 to 10
            self.setMaximumHeight(new_height + 10)  # Set maximum height to match minimum
            
            # Force layout update
            self.updateGeometry()
            if self.parent():
                self.parent().updateGeometry()
                if hasattr(self.parent(), 'update') and callable(self.parent().update):
                    self.parent().update()  # Ensure parent widget is redrawn
        except Exception as e:
            app_logger.error(f"Error adjusting size: {str(e)}")

    def toggle_edit_mode(self):
        try:
            if not self.is_editing:
                self.enable_edit_mode()
            else:
                self.save_edit_mode()
        except Exception as e:
            app_logger.error(f"Error toggling edit mode: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to edit message: {str(e)}")

    def enable_edit_mode(self):
        self.is_editing = True
        self.text.setReadOnly(False)
        self.edit_button.setIcon(QIcon("assets/check-50.svg"))
        self.edit_button.setProperty("mode", "save")

    def save_edit_mode(self):
        new_content = self.text.toPlainText().strip()
        if new_content:
            self.is_editing = False
            self.text.setReadOnly(True)
            
            # Convert the edited plain text to HTML via mistune before displaying
            markdown_parser = mistune.create_markdown()
            html_content = markdown_parser(new_content)
            self.text.setHtml(html_content)
            
            self.edit_button.setIcon(QIcon("assets/pencil-50.svg"))
            self.edit_button.setProperty("mode", "edit")
            if self.chat_app:
                self.chat_app.update_message(self.message_id, new_content)
        else:
            QMessageBox.warning(self, "Warning", "Message cannot be empty.")

    def edit_message(self):
        """Open an editor to edit the message content"""
        if not self.is_user:
            return  # Only user messages can be edited
            
        current_text = self.text.toPlainText()
        new_text, ok = QInputDialog.getMultiLineText(
            self, 'Edit Message', 'Edit your message:', current_text)
        
        if ok and new_text:  # Removed unnecessary check for new_text != current_text
            # Update the message content
            markdown_parser = mistune.create_markdown()
            html_content = markdown_parser(new_text)
            self.text.setHtml(html_content)
            
            # Update the message through the chat app
            if self.chat_app and hasattr(self.chat_app, 'update_message'):
                self.chat_app.update_message(self.message_id, new_text)
            
            # Ensure size is adjusted after content change
            self.adjust_size()