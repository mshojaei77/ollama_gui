# memory_handler.py
from langchain.memory import ConversationBufferMemory, ConversationBufferWindowMemory, ConversationSummaryMemory
from widgets.settings import SETTINGS
from logger import app_logger
from langchain.schema import HumanMessage, AIMessage

class CustomMessage(HumanMessage):
    def __init__(self, content, message_id=None):
        super().__init__(content=content)
        self.id = message_id

class CustomAIMessage(AIMessage):
    def __init__(self, content, message_id=None):
        super().__init__(content=content)
        self.id = message_id

class CustomConversationBufferMemory(ConversationBufferMemory):
    def add_user_message(self, message, message_id=None):
        """Add a user message to the memory with an ID."""
        self.chat_memory.add_user_message(CustomMessage(message, message_id))
    
    def add_ai_message(self, message, message_id=None):
        """Add an AI message to the memory with an ID."""
        self.chat_memory.add_ai_message(CustomAIMessage(message, message_id))
    
    def edit_message(self, message_id, new_content):
        """Edit a message in memory by its ID."""
        try:
            for msg in self.chat_memory.messages:
                if hasattr(msg, 'id') and msg.id == message_id:
                    msg.content = new_content
                    app_logger.info(f"Message {message_id} edited successfully in memory")
                    return True
            app_logger.warning(f"Message {message_id} not found in memory")
            return False
        except Exception as e:
            app_logger.error(f"Error editing message {message_id}: {str(e)}")
            return False

class MemoryHandler:
    def __init__(self, app):
        self.app = app
        self.memory = CustomConversationBufferMemory()

    def update_memory_settings(self):
        try:
            memory_type = SETTINGS['memory_type']
            memory_k = SETTINGS['memory_k']
            
            # Save existing messages
            existing_messages = self.memory.chat_memory.messages.copy() if hasattr(self.memory, 'chat_memory') else []
            
            # Create memory based on settings
            if memory_type == "ConversationBufferMemory":
                self.memory = CustomConversationBufferMemory()
            elif memory_type == "ConversationBufferWindowMemory":
                self.memory = ConversationBufferWindowMemory(k=memory_k)
            elif memory_type == "ConversationSummaryMemory":
                self.memory = ConversationSummaryMemory(llm=self.app.llm)
            else:
                raise ValueError(f"Unsupported memory type: {memory_type}")
            
            # Transfer existing messages to new memory
            for message in existing_messages:
                message_id = getattr(message, 'id', None)
                if hasattr(message, 'type'):
                    if message.type == 'human':
                        if hasattr(self.memory, 'add_user_message') and message_id:
                            self.memory.add_user_message(message.content, message_id)
                        else:
                            self.memory.chat_memory.add_user_message(message.content)
                    elif message.type == 'ai':
                        if hasattr(self.memory, 'add_ai_message') and message_id:
                            self.memory.add_ai_message(message.content, message_id)
                        else:
                            self.memory.chat_memory.add_ai_message(message.content)
                else:
                    # Fallback for other message types
                    self.memory.chat_memory.add_message(message)
            
            app_logger.info(f"Memory settings updated to {memory_type}")
        except Exception as e:
            app_logger.error(f"Error updating memory settings: {str(e)}")