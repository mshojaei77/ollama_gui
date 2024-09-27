from langchain_community.chat_models import ChatOllama
from langchain.schema import HumanMessage, SystemMessage
import GPUtil
import psutil

# Initialize the ChatOllama model
llm = ChatOllama(
    model="gemma2:2b",
)

# Create a list of messages
messages = [
    SystemMessage(content="You are a helpful AI assistant."),
    HumanMessage(content="Write a long story about a cat.   ")
]

# Invoke the model with the messages
response = llm.invoke(messages)

# Print the response
print(response.content)

# Get GPU usage
gpus = GPUtil.getGPUs()
gpu_usage = gpus[0].memoryUsed if gpus else 0  # Memory usage of the first GPU if available

# Get RAM usage
ram_usage = psutil.virtual_memory().used / (1024 ** 3)  # Convert to GB

print(f"GPU Memory Usage: {gpu_usage:.2f} MB")
print(f"RAM Usage: {ram_usage:.2f} GB")