from PyQt5.QtWidgets import QDialog, QMessageBox, QLabel
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from views.system_info_dialog_ui import Ui_SystemInfoDialog
import GPUtil
import psutil
import platform
import wmi
from logger import app_logger

class SystemInfoDialog(QDialog, Ui_SystemInfoDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(QIcon("path/to/icon.png"))
        self.loadStyleSheet()
        self.total_gpu_vram = 0
        self.initUI()

    def loadStyleSheet(self):
        try:
            with open("styles/system_info_dialog.qss", "r") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            app_logger.error(f"Error loading stylesheet: {str(e)}")

    def initUI(self):
        try:
            gpu_info = self.getLLMGPUInfo()
            self.gpuContent.setText(gpu_info['gpu'])
            self.vramContent.setText(gpu_info['vram'])

            cpu_info = self.getLLMCPUInfo()
            self.cpuContent.setText(cpu_info)
            self.ramContent.setText(self.getLLMMemoryInfo())

            self.calculateMaxLLMSize()

            self.closeButton.clicked.connect(self.close)
            
            for label in [self.llmSizeContent, self.gpuContent, self.vramContent, self.cpuContent, self.ramContent]:
                label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                label.setWordWrap(True)
                if isinstance(label, QLabel):
                    label.setMinimumHeight(150)

        except Exception as e:
            app_logger.error(f"Error initializing SystemInfoDialog UI: {str(e)}")

    def getLLMCPUInfo(self):
        try:
            cpu_freq = psutil.cpu_freq()
            return f"""
            <h3>🖥️ CPU Specifications</h3>
            <ul>
                <li>Total Cores: {psutil.cpu_count(logical=True)} 🧠</li>
                <li>Maximum Frequency: {cpu_freq.max:.2f}MHz ⚡</li>
                <li>Current Processor Utilization: {psutil.cpu_percent()}% 📊</li>
            </ul>
            """
        except Exception as e:
            app_logger.error(f"Error retrieving CPU info: {str(e)}")
            return "<p>❌ Unable to retrieve CPU specifications. Please verify your system configuration.</p>"

    def getLLMMemoryInfo(self):
        try:
            memory = psutil.virtual_memory()
            return f"""
            <h3>💾 RAM Specifications</h3>
            <ul>
                <li>Total RAM Capacity: {self.getSize(memory.total)} 📈</li>
                <li>Available RAM: {self.getSize(memory.available)} 🆓</li>
                <li>Current RAM Utilization: {memory.percent}% 📊</li>
            </ul>
            """
        except Exception as e:
            app_logger.error(f"Error retrieving memory info: {str(e)}")
            return "<p>❌ Unable to retrieve RAM specifications. Please verify your system configuration.</p>"

    def getLLMGPUInfo(self):
        try:
            gpu_info = "<h3>🎮 GPU Specifications</h3>"
            vram_info = "<h3>🧠 VRAM Specifications</h3>"
            self.total_gpu_vram = 0
            
            try:
                nvidia_gpus = GPUtil.getGPUs()
                if nvidia_gpus:
                    for i, gpu in enumerate(nvidia_gpus):
                        gpu_info += f"<h4>NVIDIA GPU {i + 1}:</h4><p>Model: {gpu.name} 🖥️</p>"
                        vram_info += f"""<h4>NVIDIA GPU {i + 1} VRAM:</h4>
                        <ul>
                            <li>Total Memory Capacity: {gpu.memoryTotal}MB 💾</li>
                            <li>Available Memory: {gpu.memoryFree}MB 🆓</li>
                        </ul>"""
                        self.total_gpu_vram += gpu.memoryTotal
            except Exception as nvidia_e:
                app_logger.error(f"Error retrieving NVIDIA GPU info: {str(nvidia_e)}")
            
            try:
                c = wmi.WMI()
                amd_gpus = c.Win32_VideoController(AdapterCompatibility="Advanced Micro Devices, Inc.")
                if amd_gpus:
                    for i, gpu in enumerate(amd_gpus):
                        gpu_info += f"<h4>AMD GPU {i + 1}:</h4><p>Model: {gpu.Name} 🖥️</p>"
                        vram = int(gpu.AdapterRAM) / (1024**2) if gpu.AdapterRAM else "Unknown"
                        vram_info += f"""<h4>AMD GPU {i + 1} VRAM:</h4>
                        <ul>
                            <li>Total Memory Capacity: {vram:.2f}MB 💾</li>
                        </ul>"""
                        if isinstance(vram, float):
                            self.total_gpu_vram += vram
            except Exception as amd_e:
                app_logger.error(f"Error retrieving AMD GPU info: {str(amd_e)}")
            
            return {
                'gpu': gpu_info if gpu_info != "<h3>🎮 GPU Specifications</h3>" else "<p>❌ No GPU detected. AI performance may be significantly limited.</p>",
                'vram': vram_info if vram_info != "<h3>🧠 VRAM Specifications</h3>" else "<p>❌ Unable to retrieve VRAM specifications.</p>"
            }
        except Exception as e:
            app_logger.error(f"Error in getLLMGPUInfo: {str(e)}")
            return {
                'gpu': "<p>❌ Unable to retrieve GPU specifications. Please ensure your drivers are up to date.</p>",
                'vram': "<p>❌ Unable to retrieve VRAM specifications. Please verify your system configuration.</p>"
            }

    def getSize(self, bytes, suffix="B"):
        try:
            factor = 1024
            for unit in ["", "K", "M", "G", "T", "P"]:
                if bytes < factor:
                    return f"{bytes:.2f}{unit}{suffix}"
                bytes /= factor
        except Exception as e:
            app_logger.error(f"Error converting size: {str(e)}")
            return "❌ Error"

    def calculateMaxLLMSize(self):
        try:
            quantization_bits = 4
            overhead_factor = 1.5

            max_memory_for_parameters_gb = self.total_gpu_vram / 1024 / overhead_factor
            max_llm_size_billion = round(max_memory_for_parameters_gb / (quantization_bits / 8))

            llm_size_info = f"""
            <h2>🚀 Your System's AI Capabilities</h2>
            <h1 style="color: #2ecc71; font-size: 3.5em;">🧠 {max_llm_size_billion}B Parameters</h1>
            <div>
                <h3>📊 What This Means For You</h3>
                <p>🎉 Fantastic news! Your system has the potential to handle AI models with up to {max_llm_size_billion} billion parameters. That's truly remarkable!</p>
                <div style="background-color: #fef9e7; border-left: 5px solid #f39c12; padding: 10px; margin-top: 20px;">
                    <p><strong>💡 Expert Insight:</strong> We've incorporated a buffer in our calculations to ensure optimal performance. Your actual AI capabilities may fluctuate based on your specific hardware configuration and current system load.</p>
                </div>
            </div>
            """

            self.llmSizeContent.setText(llm_size_info)
            self.llmSizeContent.setTextFormat(Qt.RichText)

        except Exception as e:
            app_logger.error(f"Error calculating max LLM size: {str(e)}")
            self.llmSizeContent.setText(f"<p>❌ Unable to calculate maximum AI model size. Please verify your system configuration.</p>")