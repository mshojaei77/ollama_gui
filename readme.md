# Ollama GUI for Windows

Ollama Chatbot is a powerful and user-friendly Windows desktop application that enables seamless interaction with various AI language models using the Ollama backend. This application provides an intuitive interface for chatting with AI models, managing conversations, and customizing settings to suit your needs.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Screenshots](#screenshots)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Features

- Easy-to-use chat interface with real-time response streaming
- Support for multiple AI models, including custom models
- Conversation management (save, load, export, clear)
- Customizable settings for fine-tuning AI behavior
- Dark mode for comfortable viewing
- System information display for hardware compatibility
- And much more!

## Prerequisites

Before installing the Ollama Chatbot, you need to have Ollama installed and running on your Windows system.

### Installing Ollama on Windows

1. **Download Ollama:**
   - Download the [Ollama Windows installer](https://ollama.com/download/OllamaSetup.exe)

2. **Install Ollama:**
   - Run the downloaded OllamaSetup.exe file
   - Follow the installation wizard instructions
   - Ollama should start automatically after installation

For more information, visit the [Ollama GitHub repository](https://github.com/ollama/ollama).

3. gui Installation
  - Download and run the latest release of Ollama Chatbot for Windows from our [releases page](https://github.com/mshojaei77/ollama_gui/releases).


## Usage

1. Ensure Ollama is running on your system (it should start automatically on Windows).
2. Launch the Ollama Chatbot application from the Start menu or desktop shortcut.
3. Choose a model from the "Model" menu or use the default "gemma2:2b" model.
4. Start chatting by typing your message in the input field and pressing Enter or clicking "Send".

## Screenshots
![image](https://github.com/user-attachments/assets/eaad3a03-b107-468c-adac-9754d55fda67)
![image](https://github.com/user-attachments/assets/a25d773c-747c-4a66-b77f-fc8cbe6cff63)
![image](https://github.com/user-attachments/assets/2ea3aaf6-8960-460a-9361-d8a06621c800)
![image](https://github.com/user-attachments/assets/4a39f4d4-5fde-437d-9deb-2515033f3d03)
![image](https://github.com/user-attachments/assets/8d38ada1-94d2-4dec-885f-cdafa98b98a4)
![image](https://github.com/user-attachments/assets/5ab4891f-eb4e-459f-959b-46049eb65a4d)

## Configuration

You can customize various aspects of the Ollama Chatbot through the Settings menu:

- **Model Parameters**: Adjust temperature, context length, top-k, top-p, and more.
- **UI Settings**: Change font size, theme, and chat bubble color.
- **Advanced Settings**: Configure max tokens, stop sequences, and penalties.
- **Memory Settings**: Choose memory type and adjust related parameters.

## Troubleshooting

- **Model Loading Issues**: Ensure the selected model is available in your Ollama installation. You can check available models by running `ollama list` in Command Prompt.
- **Connection Problems**: 
  - Verify that Ollama is running. You can check this in Task Manager or by running `ollama serve` in Command Prompt.
  - Check for any VPN or proxy interference.
- **Performance Issues**: Try using a smaller model or adjusting the context length in settings.
- **Windows Firewall**: If you're having connection issues, ensure that Ollama and Ollama Chatbot are allowed through Windows Firewall.

For more detailed troubleshooting, please refer to our [FAQ](link-to-faq) or [open an issue](link-to-issues).

## Contributing

We welcome contributions to the Ollama Chatbot project! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details on how to submit pull requests, report issues, or request features.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- The Ollama team for providing the backend AI capabilities.
- All contributors who have helped to improve this project.
- The open-source community for the various libraries and tools used in this project.

---

Enjoy engaging conversations with your AI assistant! For support, please [open an issue](https://github.com/mshojaei77/ollama_gui/issues).
