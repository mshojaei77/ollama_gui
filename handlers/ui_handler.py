# ui_handler.py
import logging
from PyQt5.QtWidgets import QDesktopWidget, QMessageBox, QHBoxLayout, QWidget, QSizePolicy
from handlers.settings_handler import SETTINGS
from widgets.message_widget import MessageWidget
from langchain_core.messages import HumanMessage, AIMessage
from logger import app_logger

class UIHandler:
    def __init__(self, app):
        self.app = app

    def center(self):
        try:
            qr = self.app.frameGeometry()
            cp = QDesktopWidget().availableGeometry().center()
            qr.moveCenter(cp)
            self.app.move(qr.topLeft())
            app_logger.info("Window centered successfully")
        except Exception as e:
            app_logger.error(f"Error centering window: {str(e)}")

    def add_system_message(self, message):
        try:
            self.app.ui.systemMessageLabel.setText(message)
            app_logger.info(f"System message added: {message}")
        except Exception as e:
            app_logger.error(f"Error adding system message: {str(e)}")
            self._show_error_message("Failed to add system message", str(e))

    def show_system_info(self):
        try:
            from widgets.system_info import SystemInfoDialog
            system_info_dialog = SystemInfoDialog(self.app)
            system_info_dialog.exec_()
            app_logger.info("System info dialog displayed")
        except Exception as e:
            app_logger.error(f"Error showing system info: {str(e)}")
            self._show_error_message("Failed to show system info", str(e))

    def show_about(self):
        try:
            about_text = (
                f"<h2>Ollama Chatbot</h2>"
                f"<p><b>Version:</b> 0.3</p>"
                f"<p><b>Copyright © 2023 Mohammad Shojaei</b></p>"
                f"<p>Ollama Chatbot is an open-source application designed to provide "
                f"a user-friendly interface for interacting with Ollama language models.</p>"
                f"<p><b>Website:</b> <a href='https://github.com/mshojaei77/ollama_gui'>https://github.com/mshojaei77/ollama_gui</a></p>"
                f"<p><b>License:</b> MIT License</p>"
                f"<p><b>Contact:</b> <a href='https://twitter.com/realshojaei'>Twitter @realshojaei</a></p>"
                f"<p>This software is provided 'as-is', without any express or implied warranty. "
                f"In no event will the authors be held liable for any damages arising from "
                f"the use of this software.</p>"
            )
            QMessageBox.about(self.app, "About Ollama Chatbot", about_text)
            app_logger.info("About dialog displayed")
        except Exception as e:
            app_logger.error(f"Error showing about dialog: {str(e)}")
            self._show_error_message("Failed to show about dialog", str(e))

    def add_message(self, content, is_user=True, message_id=None, add_to_memory=True):
        message_widget = MessageWidget(content, is_user, self.app, message_id)
        self.app.chat_handler.add_message_widget(message_widget)
        if add_to_memory:
            if is_user:
                self.app.memory_handler.memory.chat_memory.add_user_message(content)
            else:
                self.app.memory_handler.memory.chat_memory.add_ai_message(content)
        self.app.chat_handler.scroll_to_bottom()

    def _create_message_container(self, msg_widget, is_user):
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        if is_user:
            hbox.addStretch()
            hbox.addWidget(msg_widget)
        else:
            hbox.addWidget(msg_widget)
            hbox.addStretch()
        container = QWidget()
        container.setLayout(hbox)
        container.setMinimumHeight(msg_widget.sizeHint().height())
        container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        return container

    def _create_message_object(self, message, is_user):
        return HumanMessage(content=message) if is_user else AIMessage(content=message)

    def _scroll_to_bottom(self):
        # $ UI Element: chatScrollArea
        scrollbar = self.app.ui.chatScrollArea.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _update_message_font_size(self, msg_widget):
        # $ Stylesheet: Message font size
        msg_widget.text.setStyleSheet(f"font-size: {SETTINGS['font_size']}px;")

    def _show_error_message(self, title, error_message):
        QMessageBox.critical(self.app, "Error", f"{title}: {error_message}")