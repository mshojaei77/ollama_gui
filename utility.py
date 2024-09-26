# utility.py
import os
import shutil
import logging

logging

class Utility:
    @staticmethod
    def find_ollama_executable():
        try:
            ollama_path = shutil.which('ollama')
            if ollama_path:
                return ollama_path
            else:
                logging.error("Ollama executable not found in PATH.")
                return None
        except Exception as e:
            logging.error(f"Error finding Ollama executable: {str(e)}")
            return None