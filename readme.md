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

### Chat Interface
![{CB618BC4-3FCD-4408-8DEE-98F5BD2C5E10}](https://github.com/user-attachments/assets/8240ba1b-fc8e-48ec-9913-d9e760237786)

### Model Selection
![{2C654694-176D-4D85-AE99-0C8F9B25BECB}](https://github.com/user-attachments/assets/6d8079d3-4e4c-4853-a00f-2e9cda9dd4a0)

### Settings
![{CF3A2D08-B3A9-474B-8A76-46F555AD107B}](https://github.com/user-attachments/assets/04511e18-6ddf-4d8f-aa29-122c9f709811)
![{330FF573-5D30-4142-B9E7-E1EBBFD0F9F3}](https://github.com/user-attachments/assets/ac2d5e10-7482-4e54-85e8-2ab4dafb3d97)


### Dark Mode
![{D83FBB3F-D597-4638-BF87-C9ADC535BF21}](https://github.com/user-attachments/assets/a8677925-02e0-4169-b66d-44b4782fc246)


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
