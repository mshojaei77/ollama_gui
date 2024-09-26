# memory_handler.py
from langchain.memory import ConversationBufferMemory, ConversationBufferWindowMemory, ConversationSummaryMemory
from widgets.settings import SETTINGS
from logger import app_logger

class CustomConversationBufferMemory(ConversationBufferMemory):
    def edit_message(self, message_id, new_content):
        try:
            for msg in self.chat_memory.messages:
                if getattr(msg, 'id', None) == message_id:
                    msg.content = new_content
                    break
            app_logger.info(f"Message {message_id} edited successfully")
        except Exception as e:
            app_logger.error(f"Error editing message {message_id}: {str(e)}")

class MemoryHandler:
    def __init__(self, app):
        self.app = app
        self.memory = CustomConversationBufferMemory()

    def update_memory_settings(self):
        try:
            memory_type = SETTINGS['memory_type']
            memory_k = SETTINGS['memory_k']
            
            # $ Create memory based on settings
            if memory_type == "ConversationBufferMemory":
                self.memory = CustomConversationBufferMemory()
            elif memory_type == "ConversationBufferWindowMemory":
                self.memory = ConversationBufferWindowMemory(k=memory_k)
            elif memory_type == "ConversationSummaryMemory":
                self.memory = ConversationSummaryMemory(llm=self.app.llm)
            else:
                raise ValueError(f"Unsupported memory type: {memory_type}")
            
            # Transfer existing messages to new memory
            for message in self.memory.chat_memory.messages:
                self.memory.chat_memory.add_message(message)
            
            app_logger.info(f"Memory settings updated to {memory_type}")
        except Exception as e:
            app_logger.error(f"Error updating memory settings: {str(e)}")