# main.py
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from chatbot_app import ChatbotApp
from logger import app_logger
from handlers.settings_handler import SettingsHandler

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
        window.resize(1024, 768)  # Set initial size to 1024x768 pixels
        app_logger.info("Window size set to 1024x768")
        
        # Show the main window
        window.show()
        app_logger.info("ChatbotApp window shown")
        
        return app.exec_()
    except Exception as e:
        app_logger.error(f"Error initializing app: {str(e)}", exc_info=True)
        # Display error message box
        QMessageBox.critical(None, "Critical Error", f"An error occurred while initializing the application: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(initialize_app())