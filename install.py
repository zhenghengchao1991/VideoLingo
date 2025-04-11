import os, sys
import platform
import subprocess
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入必要的模块
from rich.console import Console
from rich.panel import Panel
from rich.box import DOUBLE
# from InquirerPy import inquirer # <--- 不再需要，已删除
from translations.translations import translate as t
from translations.translations import DISPLAY_LANGUAGES # 仍然需要这个
from core.config_utils import load_key, update_key # 仍然需要这个
from core.pypi_autochoose import main as choose_mirror

ascii_logo = """
__     ___     _            _     _
\ \   / (_) __| | ___  ___ | |   (_)_ __   __ _  ___
 \ \ / /| |/ _` |/ _ \/ _ \| |   | | '_ \ / _` |/ _ \\
  \ V / | | (_| |  __/ (_) | |___| | | | | (_| | (_) |
   \_/  |_|\__,_|\___|\___/|_____|_|_| |_|\__, |\___/
                                          |___/
"""

def install_package(*packages):
    # 确保pip缓存被禁用，并指定UTF-8编码
    subprocess.check_call([sys.executable, "-m", "pip", "install", *packages], env={**os.environ, "PIP_NO_CACHE_DIR": "1", "PYTHONIOENCODING": "utf-8"})

def check_nvidia_gpu():
    install_package("pynvml")
    import pynvml
    initialized = False
    try:
        pynvml.nvmlInit()
        initialized = True
        device_count = pynvml.nvmlDeviceGetCount()
        if device_count > 0:
            print(t("Detected NVIDIA GPU(s)"))
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                print(f"GPU {i}: {name}")
            return True
        else:
            print(t("No NVIDIA GPU detected"))
            return False
    except pynvml.NVMLError:
        print(t("No NVIDIA GPU detected or NVIDIA drivers not properly installed"))
        return False
    finally:
        if initialized:
            pynvml.nvmlShutdown()

def check_ffmpeg():
    console = Console()
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        console.print(Panel(t("✅ FFmpeg is already installed"), style="green"))
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        system = platform.system()
        install_cmd = ""
        extra_note = ""

        if system == "Windows":
            install_cmd = "choco install ffmpeg"
            extra_note = t("Install Chocolatey first (https://chocolatey.org/)")
        elif system == "Darwin":
            install_cmd = "brew install ffmpeg"
            extra_note = t("Install Homebrew first (https://brew.sh/)")
        elif system == "Linux":
            install_cmd = "sudo apt install ffmpeg  # Ubuntu/Debian\nsudo yum install ffmpeg  # CentOS/RHEL"
            extra_note = t("Use your distribution's package manager")

        console.print(Panel.fit(
            t("❌ FFmpeg not found\n\n") +
            f"{t('🛠️ Install using:')}\n[bold cyan]{install_cmd}[/bold cyan]\n\n" +
            (f"{t('💡 Note:')}\n{extra_note}\n\n" if extra_note else "") +
            f"{t('🔄 After installing FFmpeg, please run this installer again:')}\n[bold cyan]python install.py[/bold cyan]",
            style="red",
            title="FFmpeg Installation Required"
        ))
        raise SystemExit(t("FFmpeg is required. Please install it and run the installer again."))

def install_noto_font():
    console = Console()
    # Detect Linux distribution type
    if os.path.exists('/etc/debian_version'):
        # Debian/Ubuntu systems
        # 注意：直接运行 sudo 需要用户交互输入密码，或者配置了免密sudo。
        # 对于自动化脚本，通常不建议直接包含 sudo。但这里保持原逻辑，用户需要能执行sudo。
        cmd = ['sudo', 'apt-get', 'update', '&&', 'sudo', 'apt-get', 'install', '-y', 'fonts-noto-cjk'] # 使用 fonts-noto-cjk 通常更全
        pkg_manager = "apt-get"
    elif os.path.exists('/etc/redhat-release'):
        # RHEL/CentOS/Fedora systems
        cmd = ['sudo', 'yum', 'install', '-y', 'google-noto-sans-cjk-ttc-fonts']
        pkg_manager = "yum"
    else:
        console.print("Warning: Unrecognized Linux distribution, please install Noto fonts manually (e.g., fonts-noto-cjk)", style="yellow")
        return

    console.print(f"Attempting to install Noto fonts using {pkg_manager}...")
    try:
        # 执行命令（需要用户有sudo权限）
        result = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True, check=False) # 使用 shell=True 处理 &&
        if result.returncode == 0:
            console.print(f"✅ Successfully installed Noto fonts using {pkg_manager}", style="green")
        else:
            console.print(f"❌ Failed to install Noto fonts using {pkg_manager}. Error code: {result.returncode}", style="red")
            console.print(f"Stderr:\n{result.stderr}", style="red")
            console.print("Please try installing Noto fonts manually (e.g., 'sudo apt install fonts-noto-cjk' or 'sudo yum install google-noto-sans-cjk-ttc-fonts').", style="yellow")
    except FileNotFoundError:
        console.print(f"❌ Command 'sudo' or '{pkg_manager}' not found. Is it installed and in your PATH? Please install Noto fonts manually.", style="red")
    except Exception as e:
        console.print(f"❌ An unexpected error occurred during font installation: {e}", style="red")

def main():
    # 确保首先安装基础包
    try:
        # InquirerPy 可能不再需要，但 ruamel.yaml, requests, rich 仍然需要
        install_package("requests", "rich", "ruamel.yaml")
    except subprocess.CalledProcessError as e:
        print(f"Error installing base packages: {e}")
        sys.exit(1)

    console = Console()

    width = max(len(line) for line in ascii_logo.splitlines()) + 4
    welcome_panel = Panel(
        ascii_logo,
        width=width,
        box=DOUBLE,
        title="[bold green]🌏[/bold green]",
        border_style="bright_blue"
    )
    console.print(welcome_panel)

    # --- 语言选择部分 ---
    # Directly set language to Simplified Chinese
    selected_language = "zh-CN"
    console.print(f"Default language automatically set to: {selected_language}")

    # Update config file
    try:
        update_key("display_language", selected_language)
    except Exception as e:
        console.print(f"Error updating config file with language: {e}", style="red")
        # Decide whether to exit or continue
        # sys.exit(1)
    # --- 语言选择部分修改结束 ---

    console.print(Panel.fit(t("🚀 Starting Installation"), style="bold magenta"))

    # --- 修改镜像配置部分 ---
    # # Configure mirrors (注释掉原来的交互式选择)
    # try:
    #    if inquirer.confirm(
    #        message=t("Do you need to auto-configure PyPI mirrors? (Recommended if you have difficulty accessing pypi.org)"),
    #        default=True # 原默认值为 True
    #    ).execute():
    #        choose_mirror()
    # except Exception as e:
    #    console.print(f"Error during mirror configuration prompt: {e}", style="yellow")
    #    console.print("Skipping mirror configuration.", style="yellow")

    # 直接跳过镜像配置
    console.print("Skipping PyPI mirror auto-configuration by default.")
    # --- 镜像配置部分修改结束 ---

    # Detect system and GPU
    has_gpu = False
    console.print("⚠️ Skipping GPU check.", style="yellow")
    # pytorch_cmd = []
    # if has_gpu:
    #     console.print(Panel(t("🎮 NVIDIA GPU detected, installing CUDA version of PyTorch..."), style="cyan"))
    #     pytorch_cmd = ["torch==2.0.0", "torchaudio==2.0.0", "--index-url", "https://download.pytorch.org/whl/cu118"]
    # else:
    #     system_name = "🍎 MacOS" if platform.system() == 'Darwin' else "💻 No NVIDIA GPU"
    #     console.print(Panel(t(f"{system_name} detected, installing CPU version of PyTorch... Note: it might be slow during whisperX transcription."), style="cyan"))
    #     pytorch_cmd = ["torch==2.1.2", "torchaudio==2.1.2"]

    # if pytorch_cmd:
    #     try:
    #         install_package(*pytorch_cmd)
    #     except subprocess.CalledProcessError as e:
    #         console.print(Panel(f"❌ Failed to install PyTorch: {e}", style="red"))
    #         sys.exit(1)
    console.print("⚠️ Skipping automatic PyTorch download.", style="yellow")

    def install_requirements():
        console.print(Panel(t("Installing requirements using `pip install -r requirements.txt`"), style="cyan"))
        try:
            subprocess.check_call([
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                "requirements.txt"
            ], env={**os.environ, "PIP_NO_CACHE_DIR": "1", "PYTHONIOENCODING": "utf-8"})
            console.print("✅ Requirements installed successfully.", style="green")
        except subprocess.CalledProcessError as e:
            console.print(Panel(t("❌ Failed to install requirements:") + f"\n{e}", style="red"))
            sys.exit(1)
        except FileNotFoundError:
            console.print(Panel("❌ Error: requirements.txt not found in the current directory.", style="red"))
            sys.exit(1)

    if platform.system() == 'Linux':
        install_noto_font()

    install_requirements()
    check_ffmpeg()

    panel1_text = (
        t("Installation completed") + "\n\n" +
        t("Now I will run this command to start the application:") + "\n" +
        "[bold]streamlit run st.py[/bold]\n\n" +
        t("Note: First startup may take up to 1 minute")
    )
    console.print(Panel(panel1_text, style="bold green", title="Installation Complete"))

    panel2_text = (
        t("If the application fails to start:") + "\n" +
        "1. " + t("Check your network connection") + "\n" +
        "2. " + t("Re-run the installer: [bold]python install.py[/bold]")
    )
    console.print(Panel(panel2_text, style="yellow", title="Troubleshooting"))

    # 自动启动应用
    console.print("\nAttempting to start the application automatically...")
    try:
        subprocess.Popen(["streamlit", "run", "st.py"])
        console.print("✅ Application started in the background.", style="green")
    except FileNotFoundError:
        console.print("❌ Error: 'streamlit' command not found. Make sure Streamlit is installed correctly and in your PATH.", style="red")
    except Exception as e:
        console.print(f"❌ An error occurred while trying to start the application: {e}", style="red")

if __name__ == "__main__":
    main()
