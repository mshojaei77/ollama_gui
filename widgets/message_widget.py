import logging
import uuid
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QTextEdit, QPushButton, QSizePolicy, QMessageBox, QFrame
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from logger import app_logger  # Importing the logger

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
        self.text.setMarkdown(message)
        self.text.setReadOnly(True)
        self.text.setFont(QFont('SF Pro Text', 13))
        self.text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text.setFrameStyle(QFrame.NoFrame)
        
        self.text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        self.text.document().contentsChanged.connect(self.adjust_size)

        # $ Text Edit Stylesheet
        self.text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {'#F0F8FF' if self.is_user else '#D8E4FF'};
                border: none;
                border-radius: 18px;
                padding: 15px 20px;
                color: #333333;
            }}
        """)

    def create_edit_button(self):
        # $ Edit Button UI Element
        self.edit_button = QPushButton("Edit")
        self.edit_button.setFixedSize(70, 30)
        self.edit_button.clicked.connect(self.toggle_edit_mode)
        
        # $ Edit Button Stylesheet
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
            new_height = int(doc_height) + 40
            
            self.text.setMinimumWidth(min_width)
            self.text.setMaximumWidth(max_width)
            self.text.setFixedHeight(new_height)
            self.setFixedHeight(new_height + 20)

            # Force layout update
            self.updateGeometry()
            if self.parent():
                self.parent().updateGeometry()
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
        self.edit_button.setText("Save")
        # $ Edit Button Stylesheet (Save mode)
        self.edit_button.setStyleSheet("""
            QPushButton {
                background-color: #98FB98;
                color: #333333;
                border: none;
                border-radius: 15px;
                padding: 5px 10px;
                font-family: 'SF Pro Text';
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #90EE90;
            }
            QPushButton:pressed {
                background-color: #3CB371;
            }
        """)

    def save_edit_mode(self):
        new_content = self.text.toPlainText().strip()
        if new_content:
            self.is_editing = False
            self.text.setReadOnly(True)
            self.edit_button.setText("Edit")
            # $ Edit Button Stylesheet (Edit mode)
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
            if self.chat_app:
                self.chat_app.update_message(self.message_id, new_content)
        else:
            QMessageBox.warning(self, "Warning", "Message cannot be empty.")