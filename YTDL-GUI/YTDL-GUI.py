import sys
import os
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
import subprocess
import csv
import time
import uuid
import re
import zipfile
import tarfile
import platform
import shutil
from datetime import timedelta

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QComboBox,
    QMessageBox, QProgressBar, QSpinBox, QDialog, QFormLayout, QMenuBar, QMenu,
    QCheckBox, QTabWidget, QTextEdit, QInputDialog, QAbstractItemView
)
from PySide6.QtGui import QPixmap, QAction, QIcon, QFont, QPalette, QColor
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QMetaObject, QEvent

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------- Color Variables ----------------
DARK_COLOR_PRIMARY = "#2979FF"
DARK_COLOR_SECONDARY = "#739EC9"
DARK_COLOR_PRIMARY_DARK = "#78909C"
DARK_COLOR_DANGER = "#CF6679"
DARK_COLOR_NEUTRAL = "#4FC3F7"
DARK_COLOR_BACKGROUND = "#121212"
DARK_COLOR_TEXT = "#f8fafc"
DARK_COLOR_TEXT_MENU = "#64B5F6"
DARK_COLOR_ACCENT = "#44444E"
DARK_COLOR_SURFACE = "#1E1E1E"
DARK_COLOR_GRID = "#333333"
DARK_COLOR_HOVER = "#154D71"
DARK_COLOR_ALTERNATE = "#2A2A2A"

LIGHT_COLOR_PRIMARY = "#2196F3"
LIGHT_COLOR_SECONDARY = "#4CAF50"
LIGHT_COLOR_PRIMARY_DARK = "#90A4AE"
LIGHT_COLOR_DANGER = "#F44336"
LIGHT_COLOR_NEUTRAL = "#29B6F6"
LIGHT_COLOR_BACKGROUND = "#FFFFFF"
LIGHT_COLOR_TEXT = "#020618"
LIGHT_COLOR_TEXT_MENU = "#42A5F5"
LIGHT_COLOR_ACCENT = "#FFEB3B"
LIGHT_COLOR_SURFACE = "#F5F5F5"
LIGHT_COLOR_GRID = "#E0E0E0"
LIGHT_COLOR_HOVER = "#E3F2FD"
LIGHT_COLOR_ALTERNATE = "#FAFAFA"

# ---------------- Constants ----------------
def get_app_dir():
    if getattr(sys, 'frozen', False):
        # PyInstaller bundle
        return os.path.dirname(sys.executable)
    else:
        # Development
        return os.path.dirname(os.path.abspath(__file__))

def get_user_data_dir(app_name="YouTubeDownloader"):
    """Get user-specific data directory for config/cache files."""
    system = platform.system().lower()
    if system == "windows":
        # Use %APPDATA%\AppName
        return os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), app_name)
    elif system == "darwin":
        # Use ~/Library/Application Support/AppName
        return os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', app_name)
    else:  # Linux/Unix
        # Use ~/.config/AppName
        return os.path.join(os.path.expanduser('~'), '.config', app_name)

CONFIG_DIR = os.path.join(get_user_data_dir(), ".youtube_downloader")
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
QUEUE_PATH = os.path.join(CONFIG_DIR, "queue.json")
THUMB_CACHE_DIR = os.path.join(get_user_data_dir(), ".youtube_downloader_thumbs")
os.makedirs(THUMB_CACHE_DIR, exist_ok=True)
FFMPEG_DIR = os.path.join(get_user_data_dir(), "ffmpeg_bin")

YTDLP_NAME = "yt-dlp.exe" if platform.system().lower() == "windows" else "yt-dlp"
FFMPEG_NAME = "ffmpeg.exe" if platform.system().lower() == "windows" else "ffmpeg"

QUALITY_OPTIONS = ["بهترین", "بدترین", "1080p", "720p", "480p", "360p", "144p"]
FORMAT_OPTIONS = ["ویدیو و صدا", "فقط صدا"]
VIDEO_FORMAT_OPTIONS = ["mp4", "mkv", "mov", "avi", "webm"]
SUBTITLE_LANGS = ["هیچ", "انگلیسی (en)", "فارسی (fa)"]
THEME_OPTIONS = ["Auto", "Light", "Dark"]

# ---------------- Helper Functions ----------------

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def download_with_progress(url, download_path, tool_name):
    """Download with progress logging."""
    try:
        response = requests.get(url, stream=True, timeout=(30, 300))
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0

        with open(download_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0:
                        percent = (downloaded_size / total_size) * 100
                        print(f"[{tool_name}] Downloaded {percent:.1f}% ({format_file_size(downloaded_size)} / {format_file_size(total_size)})", end='\r')
                        logging.info(f"[{tool_name}] {percent:.1f}%")
        print(f"\n[{tool_name}] Download completed.")
        logging.info(f"[{tool_name}] Download completed.")
    except Exception as e:
        if os.path.exists(download_path):
            os.remove(download_path)
        raise IOError(f"خطا در دانلود {tool_name}: {e}")

def download_yt_dlp():
    system = platform.system().lower()
    if system == "windows":
        url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    else:
        url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
    app_dir = get_app_dir()
    download_path = os.path.join(app_dir, YTDLP_NAME + ".tmp")
    download_with_progress(url, download_path, "yt-dlp")
    final_path = os.path.join(app_dir, YTDLP_NAME)
    os.replace(download_path, final_path)
    if not system == "windows":
        os.chmod(final_path, 0o755)
    logging.info(f"yt-dlp downloaded to {final_path}")
    return final_path

def download_ffmpeg():
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "windows":
        url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        file_ext = ".zip"
    elif system == "darwin":
        url = "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"
        file_ext = ".zip"
    elif system == "linux":
        if "arm" in machine or "aarch64" in machine:
            url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz"
        else:
            url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        file_ext = ".tar.xz"
    else:
        raise OSError("سیستم عامل پشتیبانی نمی‌شود.")
    
    app_dir = get_app_dir()
    os.makedirs(os.path.join(app_dir, "ffmpeg_bin"), exist_ok=True)
    download_path = os.path.join(app_dir, f"ffmpeg{file_ext}.tmp")
    
    download_with_progress(url, download_path, "ffmpeg")
    
    zip_path = download_path.replace('.tmp', '')
    os.replace(download_path, zip_path)
    
    try:
        if file_ext == ".zip":
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(app_dir)
        elif file_ext == ".tar.xz":
            with tarfile.open(zip_path, 'r:xz') as tar_ref:
                tar_ref.extractall(app_dir)
        
        # Copy binaries to app dir
        for root, _, files in os.walk(app_dir):
            for file in files:
                if file in [FFMPEG_NAME, "ffprobe", "ffprobe.exe", "ffplay", "ffplay.exe"]:
                    src = os.path.join(root, file)
                    dst = os.path.join(app_dir, file)
                    shutil.copy(src, dst)
                    if not system == "windows":
                        os.chmod(dst, 0o755)
        
        os.remove(zip_path)
        # Clean up extracted dir if any
        extracted_dir = os.path.join(app_dir, "ffmpeg-" + re.search(r'ffmpeg-([\d.-]+)', zip_path).group(1)) if re.search(r'ffmpeg-([\d.-]+)', zip_path) else None
        if extracted_dir and os.path.exists(extracted_dir):
            shutil.rmtree(extracted_dir)
    except Exception as e:
        raise IOError(f"خطا در استخراج ffmpeg: {e}")
    
    final_path = os.path.join(app_dir, FFMPEG_NAME)
    logging.info(f"ffmpeg downloaded to {final_path}")
    return final_path

def get_yt_dlp_path():
    # Check system PATH
    yt_path = shutil.which(YTDLP_NAME)
    if yt_path:
        logging.info(f"yt-dlp found in system PATH: {yt_path}")
        return yt_path
    
    # Check app dir
    app_yt_path = os.path.join(get_app_dir(), YTDLP_NAME)
    if os.path.exists(app_yt_path):
        logging.info(f"yt-dlp found in app dir: {app_yt_path}")
        return app_yt_path
    
    # Download
    logging.info("yt-dlp not found, downloading...")
    try:
        return download_yt_dlp()
    except Exception as e:
        logging.error(f"Failed to download yt-dlp: {e}")
        return None

def get_ffmpeg_path():
    # Check system PATH
    ff_path = shutil.which(FFMPEG_NAME)
    if ff_path:
        logging.info(f"ffmpeg found in system PATH: {ff_path}")
        return ff_path
    
    # Check app dir
    app_ff_path = os.path.join(get_app_dir(), FFMPEG_NAME)
    if os.path.exists(app_ff_path):
        logging.info(f"ffmpeg found in app dir: {app_ff_path}")
        if platform.system().lower() != "windows":
            try:
                os.chmod(app_ff_path, 0o755)
            except OSError as e:
                logging.error(f"Error setting permissions for ffmpeg: {e}")
        return app_ff_path
    
    # Download
    logging.info("ffmpeg not found, downloading...")
    try:
        return download_ffmpeg()
    except Exception as e:
        logging.error(f"Failed to download ffmpeg: {e}")
        return None

def get_yt_dlp_version():
    path = get_yt_dlp_path()
    if not path:
        return None
    try:
        result = subprocess.run([path, '--version'], capture_output=True, text=True, check=False)
        version = result.stdout.strip().split('\n')[0] if result.returncode == 0 else None
        logging.info(f"yt-dlp version: {version}")
        return version
    except Exception as e:
        logging.error(f"Error getting yt-dlp version: {e}")
        return None

def get_ffmpeg_version():
    path = get_ffmpeg_path()
    if not path:
        return None
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        result = subprocess.run([path, '-version'], capture_output=True, text=True, check=False, creationflags=creation_flags)
        version = "installed" if result.returncode == 0 else None
        if version:
            logging.info("ffmpeg version: installed")
        return version
    except Exception as e:
        logging.error(f"Error getting ffmpeg version: {e}")
        return None

def load_json_file(file_path, default_data=None):
    if not os.path.exists(file_path):
        return default_data if default_data is not None else {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, (dict, list)):
            raise ValueError("Invalid JSON structure")
        return data
    except (json.JSONDecodeError, ValueError) as e:
        logging.error(f"خطا در بارگذاری JSON از {file_path}: {e}")
        QMessageBox.warning(None, "خطای فایل", f"فایل {file_path} خراب است. داده پیش‌فرض استفاده می‌شود.")
        return default_data if default_data is not None else {}

def save_json_file(file_path, data):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        backup_path = file_path + ".bak"
        if os.path.exists(file_path):
            os.replace(file_path, backup_path)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        if os.path.exists(backup_path):
            os.remove(backup_path)
    except IOError as e:
        logging.error(f"خطا در ذخیره فایل {file_path}: {e}")
        if 'backup_path' in locals() and os.path.exists(backup_path):
            os.replace(backup_path, file_path)

def format_file_size(size_bytes):
    if size_bytes is None:
        return "نامشخص"
    try:
        size_bytes = float(size_bytes)
        if size_bytes >= 1024**3:
            return f"{size_bytes / 1024**3:.2f} GB"
        elif size_bytes >= 1024**2:
            return f"{size_bytes / 1024**2:.2f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.2f} KB"
        else:
            return f"{size_bytes:.2f} B"
    except (ValueError, TypeError):
        return "نامشخص"

def format_duration(duration_sec):
    if duration_sec is None:
        return "نامشخص"
    try:
        return str(timedelta(seconds=int(duration_sec)))
    except (ValueError, TypeError):
        return "نامشخص"

def format_speed(speed_bytes):
    if speed_bytes is None or speed_bytes == 0:
        return ""
    try:
        speed_bytes = float(speed_bytes)
        if speed_bytes >= 1024**2:
            return f"{speed_bytes / 1024**2:.2f} MB/s"
        elif speed_bytes >= 1024:
            return f"{speed_bytes / 1024:.2f} KB/s"
        else:
            return f"{speed_bytes:.2f} B/s"
    except (ValueError, TypeError):
        return ""

def format_eta(eta_seconds):
    if eta_seconds is None:
        return ""
    try:
        return str(timedelta(seconds=int(eta_seconds)))
    except (ValueError, TypeError):
        return ""

def check_file_exists(save_folder, title, ext):
    safe_title = "".join(c for c in title if c.isalnum() or c in " ._()")
    file_path = os.path.join(save_folder, f"{safe_title}.{ext}")
    return os.path.exists(file_path), file_path

def check_partial_file(save_folder, title, ext):
    safe_title = "".join(c for c in title if c.isalnum() or c in " ._()")
    part_path = os.path.join(save_folder, f"{safe_title}.{ext}.part")
    return os.path.exists(part_path), part_path

def delete_partial_files(save_folder, title, ext, force_delete=False):
    safe_title = "".join(c for c in title if c.isalnum() or c in " ._()")
    file_path = os.path.join(save_folder, f"{safe_title}.{ext}")
    part_path = file_path + '.part'
    paths = [file_path, part_path] if force_delete else [part_path]
    for path in paths:
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError as e:
                logging.error(f"خطا در حذف فایل {path}: {e}")

def download_thumbnail(url, save_path):
    session = requests.Session()
    retry = Retry(connect=5, read=5, redirect=5, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    try:
        response = session.get(url, timeout=30)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        return False
    except Exception as e:
        logging.error(f"خطا در دانلود تامنیل: {e}")
        return False

def is_dark_mode():
    if hasattr(QApplication, "styleHints"):
        return QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    return False

# ---------------- Worker Classes (Threads) ----------------
class DownloaderThread(QThread):
    download_progress = Signal(dict)
    postprocess_progress = Signal(dict)
    download_finished = Signal(dict)
    download_error = Signal(str, str)
    download_cancelled = Signal(str)
    download_step = Signal(str, str)
    log_line = Signal(str)

    def __init__(self, id, url, ydl_opts, yt_dlp_path, ffmpeg_path, parent=None):
        super().__init__(parent)
        self.id = id
        self.url = url
        self.ydl_opts = ydl_opts
        self.yt_dlp_path = yt_dlp_path
        self.ffmpeg_path = ffmpeg_path
        self.is_cancelled = False
        self.is_paused = False
        self.lock = threading.Lock()
        self.process = None
        self.filename = None

    def run(self):
        with self.lock:
            if self.is_cancelled or self.is_paused:
                self.download_cancelled.emit(self.id)
                return

        self.download_step.emit(self.id, "استخراج اطلاعات...")

        # Extract info using yt-dlp -J
        try:
            cmd_extract = [self.yt_dlp_path, "-j", self.url]
            result = subprocess.run(cmd_extract, capture_output=True, text=True, check=True)
            info_dict = json.loads(result.stdout.strip())
            self.log_line.emit(f"Extracted info for {info_dict.get('title', 'Unknown')}")
        except subprocess.CalledProcessError as e:
            self.download_error.emit(f"خطا در استخراج اطلاعات: {e.stderr}", self.id)
            return
        except Exception as e:
            self.download_error.emit(f"خطای غیرمنتظره در استخراج: {e}", self.id)
            return

        with self.lock:
            if self.is_cancelled or self.is_paused:
                self.download_cancelled.emit(self.id)
                return

        self.download_step.emit(self.id, "شروع دانلود...")

        # Build CLI args
        cli_args = [
            "--output", self.ydl_opts['outtmpl']['default'],
            "-f", str(self.ydl_opts['format']),
            "--retries", "10",
            "--continue",
            "-v"  # Verbose for logging
        ]
        if self.ffmpeg_path:
            cli_args += ["--ffmpeg-location", self.ffmpeg_path]
        if self.ydl_opts.get('proxy'):
            cli_args += ["--proxy", self.ydl_opts['proxy']]
        # Postprocessors
        if self.ydl_opts.get('format') == 'bestaudio/best':
            cli_args += ["--extract-audio", "--audio-format", "mp3"]
        else:
            pp = self.ydl_opts['postprocessors'][0]
            if pp['key'] == 'FFmpegVideoConvertor':
                cli_args += ["--recode-video", pp['preferedformat']]
        # Subtitles
        if self.ydl_opts.get('writesubtitles', False):
            cli_args += ["--write-subs", "--write-auto-sub"]
            if 'subtitleslangs' in self.ydl_opts:
                cli_args += ["--sub-langs", ",".join(self.ydl_opts['subtitleslangs'])]
            pp_sub = next((p for p in self.ydl_opts.get('postprocessors', []) if p['key'] == 'FFmpegSubtitlesConvertor'), None)
            if pp_sub:
                cli_args += ["--convert-subs", pp_sub['format']]

        cmd = [self.yt_dlp_path] + cli_args + [self.url]

        self.process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, universal_newlines=True
        )

        try:
            for line in iter(self.process.stdout.readline, ''):
                line = line.strip()
                if not line:
                    continue
                self.log_line.emit(line)
                with self.lock:
                    if self.is_cancelled or self.is_paused:
                        self.process.terminate()
                        self.process.wait()
                        self.download_cancelled.emit(self.id)
                        return

                if '[download]' in line:
                    d = self.parse_progress_line(line)
                    if d:
                        self.download_progress.emit(d)

                if '[Merger]' in line or '[Video Remuxing]' in line or '[FFmpeg]' in line:
                    self.postprocess_progress.emit({'id': self.id, 'status': 'postprocess', 'filename': self.filename or 'Unknown'})

            self.process.wait()
            if self.process.returncode == 0:
                info_dict['id'] = self.id
                # Guess filepath from outtmpl
                safe_title = re.sub(r'[^\w\s-]', '', info_dict.get('title', 'Unknown')).strip()
                ext = 'mp3' if self.ydl_opts.get('format') == 'bestaudio/best' else self.ydl_opts['postprocessors'][0]['preferedformat'] if self.ydl_opts.get('postprocessors') else 'mp4'
                info_dict['filepath'] = os.path.join(self.ydl_opts['outtmpl']['default'].rsplit('.', 1)[0], f"{safe_title}.{ext}")
                self.download_finished.emit(info_dict)
            else:
                self.download_error.emit("خطا در دانلود (return code != 0)", self.id)
        except Exception as e:
            self.download_error.emit(f"خطا در فرآیند دانلود: {e}", self.id)

    def parse_progress_line(self, line):
        d = {'id': self.id, 'status': 'downloading'}
        # Percent
        percent_match = re.search(r'\[download\]\s+([\d.]+)%', line)
        if percent_match:
            d['_percent_str'] = percent_match.group(1) + '%'
        # Downloaded size
        size_match = re.search(r'of\s+([\d.]+[KMG]i?B)', line)
        if size_match:
            d['downloaded_bytes'] = size_match.group(1)
        # Speed
        speed_match = re.search(r'at\s+([\d.]+[KMG]i?B/s)', line)
        if speed_match:
            d['speed'] = float(re.search(r'([\d.]+)', speed_match.group(1)).group(1))
            unit = re.search(r'([KMG]i?B/s)', speed_match.group(1)).group(1)
            if 'K' in unit:
                d['speed'] *= 1024
            elif 'M' in unit:
                d['speed'] *= 1024**2
            elif 'G' in unit:
                d['speed'] *= 1024**3
        # ETA
        eta_match = re.search(r'ETA\s+([\d:]+)', line)
        if eta_match:
            eta_str = eta_match.group(1)
            d['eta'] = sum(int(x) * 60**i for i, x in enumerate(reversed(eta_str.split(':'))))
        # Destination filename
        dest_match = re.search(r'Destination:\s+(.*)', line)
        if dest_match:
            self.filename = dest_match.group(1).strip()
        return d if '_percent_str' in d else None

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تنظیمات")
        self.setFixedSize(400, 380)
        self.parent_app = parent

        main_layout = QFormLayout()

        self.folder_label = QLineEdit(self.parent_app.settings.get("save_folder", ""))
        self.folder_label.setReadOnly(True)
        folder_button = QPushButton("انتخاب پوشه")
        folder_button.clicked.connect(self.select_folder)
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(folder_button)
        main_layout.addRow("پوشه ذخیره:", folder_layout)

        self.format_combo = QComboBox()
        self.format_combo.addItems(FORMAT_OPTIONS)
        self.format_combo.setCurrentText(self.parent_app.settings.get("format", "ویدیو و صدا"))
        main_layout.addRow("فرمت دانلود پیش‌فرض:", self.format_combo)

        self.video_format_combo = QComboBox()
        self.video_format_combo.addItems(VIDEO_FORMAT_OPTIONS)
        self.video_format_combo.setCurrentText(self.parent_app.settings.get("video_format", "mp4"))
        main_layout.addRow("فرمت خروجی ویدیو:", self.video_format_combo)

        self.concurrency_spin = QSpinBox()
        self.concurrency_spin.setRange(1, 10)
        self.concurrency_spin.setValue(self.parent_app.settings.get("concurrency", 3))
        main_layout.addRow("حداکثر دانلود همزمان:", self.concurrency_spin)
        
        self.proxy_input = QLineEdit(self.parent_app.settings.get("proxy", ""))
        self.proxy_input.setPlaceholderText("http://proxy.example.com:8080")
        main_layout.addRow("پروکسی:", self.proxy_input)
        
        self.subtitle_lang_combo = QComboBox()
        self.subtitle_lang_combo.addItems(SUBTITLE_LANGS)
        self.subtitle_lang_combo.setCurrentText(self.parent_app.settings.get("subtitle_lang", "هیچ"))
        main_layout.addRow("دانلود زیرنویس:", self.subtitle_lang_combo)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEME_OPTIONS)
        self.theme_combo.setCurrentText(self.parent_app.settings.get("theme", "Auto"))
        main_layout.addRow("تم برنامه:", self.theme_combo)
        
        self.clear_data_on_exit = QCheckBox("پاک کردن صف دانلود هنگام خروج")
        self.clear_data_on_exit.setChecked(self.parent_app.settings.get("clear_on_exit", False))
        main_layout.addRow(self.clear_data_on_exit)
        
        self.delete_partial_on_cancel = QCheckBox("حذف خودکار فایل‌های ناقص هنگام لغو دانلود")
        self.delete_partial_on_cancel.setChecked(self.parent_app.settings.get("delete_partial_on_cancel", False))
        main_layout.addRow(self.delete_partial_on_cancel)

        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("تایید")
        self.cancel_btn = QPushButton("لغو")
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        main_layout.addRow(button_layout)

        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        self.setLayout(main_layout)
    
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "انتخاب پوشه ذخیره")
        if folder:
            self.folder_label.setText(folder)

class SaveDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ذخیره اطلاعات")
        self.setFixedSize(400, 300)
        self.checkboxes = {}

        main_layout = QVBoxLayout()
        form_layout = QFormLayout()

        fields = ["عنوان", "URL", "حجم", "تعداد بازدید", "تاریخ آپلود", "کیفیت", "مسیر ذخیره", "لینک تامنیل"]
        for field in fields:
            checkbox = QCheckBox(field)
            checkbox.setChecked(True)
            self.checkboxes[field] = checkbox
            form_layout.addRow(checkbox)
            
        main_layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("ذخیره")
        self.cancel_btn = QPushButton("لغو")
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def get_selected_fields(self):
        return [field for field, checkbox in self.checkboxes.items() if checkbox.isChecked()]

class App(QWidget):
    ui_update_signal = Signal(str, bool)
    video_info_loaded = Signal(int, dict)
    update_progress = Signal(str, float, str, str, str)  # id, percent, downloaded_str, speed_str, eta_str
    log_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("دانلودکننده یوتیوب")
        self.setGeometry(100, 100, 1200, 700)
        self.settings = {}
        self.download_queue = []
        self.completed_downloads = []
        self.active_downloads = []
        self.id_to_row = {}
        self.downloading_all = False
        self.yt_dlp_version = None
        self.ffmpeg_version = None
        self.yt_dlp_path = None
        self.ffmpeg_path = None
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.fetch_cancelled = False
        self.ask_delete_partial = False
        self.progress_emit_counter = {}  # To rate-limit progress emits

        self.ui_update_signal.connect(self.update_ui_from_thread)
        self.video_info_loaded.connect(self._add_to_table_from_thread)
        self.update_progress.connect(self._update_progress_ui)
        self.log_signal.connect(self.log_message)

        self.load_settings()
        self.apply_theme()
        self.init_ui()
        self.load_queue()
        self.check_dependencies(silent=True)
        self.restore_queue_to_table()

        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self._refresh_ui)
        self.ui_timer.start(1000)

    def log_message(self, message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def init_ui(self):
        main_layout = QVBoxLayout()

        menu_bar = QMenuBar()
        file_menu = menu_bar.addMenu("فایل")
        file_menu.addAction("وارد کردن لیست").triggered.connect(self.import_from_file)
        export_menu = file_menu.addMenu("خروجی گرفتن")
        export_menu.addAction("TXT").triggered.connect(lambda: self.export_to_file('txt'))
        export_menu.addAction("JSON").triggered.connect(lambda: self.export_to_file('json'))
        export_menu.addAction("CSV").triggered.connect(lambda: self.export_to_file('csv'))
        file_menu.addAction("خروجی لیست دانلود شده‌ها").triggered.connect(self.export_completed_list)
        file_menu.addAction("پاک کردن صف").triggered.connect(self.clear_queue)

        settings_menu = menu_bar.addMenu("تنظیمات")
        settings_menu.addAction("تنظیمات").triggered.connect(self.show_settings_dialog)

        main_layout.addWidget(menu_bar)

        input_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("آدرس ویدیو یا لیست پخش یوتیوب را وارد کنید...")
        self.add_btn = QPushButton("اضافه کردن به صف")
        self.add_btn.clicked.connect(self.add_to_queue)
        self.cancel_add_btn = QPushButton("لغو اضافه کردن")
        self.cancel_add_btn.clicked.connect(self.cancel_add_to_queue)
        self.cancel_add_btn.setEnabled(False)
        input_layout.addWidget(self.url_input)
        input_layout.addWidget(self.add_btn)
        input_layout.addWidget(self.cancel_add_btn)
        main_layout.addLayout(input_layout)

        self.tab_widget = QTabWidget()
        self.download_tab = QWidget()
        download_layout = QVBoxLayout()

        search_layout = QHBoxLayout()
        search_label = QLabel("جستجو:")
        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(self.filter_table)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        download_layout.addLayout(search_layout)

        self.table = QTableWidget(0, 12)  # افزایش به 12 ستون برای حجم دانلود شده
        self.table.setHorizontalHeaderLabels(["عنوان", "لینک", "حجم کل", "مدت زمان", "کیفیت", "فرمت", "زیرنویس", "وضعیت", "پیشرفت", "حجم دانلود شده", "سرعت", "زمان باقی‌مانده"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setSectionResizeMode(5, QHeaderView.Interactive)
        header.setSectionResizeMode(6, QHeaderView.Interactive)
        header.setSectionResizeMode(7, QHeaderView.Interactive)
        header.setSectionResizeMode(8, QHeaderView.Interactive)
        header.setSectionResizeMode(9, QHeaderView.Interactive)
        header.setSectionResizeMode(10, QHeaderView.Interactive)
        header.setSectionResizeMode(11, QHeaderView.Interactive)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(lambda pos: self.show_context_menu(pos, "download"))
        download_layout.addWidget(self.table)

        button_layout = QHBoxLayout()
        self.start_download_btn = QPushButton("شروع دانلود")
        self.start_download_btn.clicked.connect(self.start_downloads)
        self.cancel_download_btn = QPushButton("لغو تمام دانلودها")
        self.cancel_download_btn.clicked.connect(self.cancel_all_downloads)
        self.cancel_download_btn.setEnabled(False)
        self.remove_selected_btn = QPushButton("حذف انتخاب‌شده‌ها")
        self.remove_selected_btn.clicked.connect(self.remove_selected_items)
        button_layout.addWidget(self.start_download_btn)
        button_layout.addWidget(self.cancel_download_btn)
        button_layout.addWidget(self.remove_selected_btn)
        download_layout.addLayout(button_layout)

        self.download_tab.setLayout(download_layout)
        self.tab_widget.addTab(self.download_tab, "صف دانلود")

        self.completed_tab = QWidget()
        completed_layout = QVBoxLayout()
        self.completed_table = QTableWidget(0, 8)
        self.completed_table.setHorizontalHeaderLabels(["عنوان", "لینک", "حجم", "مدت زمان", "کیفیت", "وضعیت", "تاریخ آپلود", "مسیر فایل"])
        completed_header = self.completed_table.horizontalHeader()
        completed_header.setSectionResizeMode(QHeaderView.Stretch)
        self.completed_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.completed_table.setAlternatingRowColors(True)
        self.completed_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.completed_table.customContextMenuRequested.connect(lambda pos: self.show_context_menu(pos, "completed"))
        completed_layout.addWidget(self.completed_table)
        self.completed_tab.setLayout(completed_layout)
        self.tab_widget.addTab(self.completed_tab, "دانلود شده‌ها")

        main_layout.addWidget(self.tab_widget)

        self.status_label = QLabel("آماده.")
        main_layout.addWidget(self.status_label)

        log_label = QLabel("لاگ عملیات:")
        main_layout.addWidget(log_label)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        main_layout.addWidget(self.log_text)

        self.setLayout(main_layout)

    def apply_theme(self):
        theme = self.settings.get("theme", "Auto")
        use_dark = (theme == "Dark") or (theme == "Auto" and is_dark_mode())

        color_schemes = {
            "dark": {
                "PRIMARY": DARK_COLOR_PRIMARY,
                "SECONDARY": DARK_COLOR_SECONDARY,
                "PRIMARY_DARK": DARK_COLOR_PRIMARY_DARK,
                "DANGER": DARK_COLOR_DANGER,
                "NEUTRAL": DARK_COLOR_NEUTRAL,
                "BACKGROUND": DARK_COLOR_BACKGROUND,
                "TEXT": DARK_COLOR_TEXT,
                "MENU_TEXT": DARK_COLOR_TEXT_MENU,
                "ACCENT": DARK_COLOR_ACCENT,
                "SURFACE": DARK_COLOR_SURFACE,
                "GRID": DARK_COLOR_GRID,
                "HOVER": DARK_COLOR_HOVER,
                "ALTERNATE": DARK_COLOR_ALTERNATE
            },
            "light": {
                "PRIMARY": LIGHT_COLOR_PRIMARY,
                "SECONDARY": LIGHT_COLOR_SECONDARY,
                "PRIMARY_DARK": LIGHT_COLOR_PRIMARY_DARK,
                "DANGER": LIGHT_COLOR_DANGER,
                "NEUTRAL": LIGHT_COLOR_NEUTRAL,
                "BACKGROUND": LIGHT_COLOR_BACKGROUND,
                "TEXT": LIGHT_COLOR_TEXT,
                "MENU_TEXT": LIGHT_COLOR_TEXT_MENU,
                "ACCENT": LIGHT_COLOR_ACCENT,
                "SURFACE": LIGHT_COLOR_SURFACE,
                "GRID": LIGHT_COLOR_GRID,
                "HOVER": LIGHT_COLOR_HOVER,
                "ALTERNATE": LIGHT_COLOR_ALTERNATE
            }
        }

        colors = color_schemes["dark" if use_dark else "light"]

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(colors["BACKGROUND"]))
        palette.setColor(QPalette.WindowText, QColor(colors["TEXT"]))
        palette.setColor(QPalette.Base, QColor(colors["SURFACE"]))
        palette.setColor(QPalette.AlternateBase, QColor(colors["ALTERNATE"]))
        palette.setColor(QPalette.ToolTipBase, QColor(colors["BACKGROUND"]))
        palette.setColor(QPalette.ToolTipText, QColor(colors["TEXT"]))
        palette.setColor(QPalette.Text, QColor(colors["MENU_TEXT"]))
        palette.setColor(QPalette.Button, QColor(colors["PRIMARY"]))
        palette.setColor(QPalette.ButtonText, QColor(colors["TEXT"]))
        palette.setColor(QPalette.Highlight, QColor(colors["PRIMARY_DARK"]))
        palette.setColor(QPalette.HighlightedText, QColor(colors["TEXT"]))
        QApplication.setPalette(palette)

        stylesheet = f"""
            QWidget {{
                background-color: {colors['BACKGROUND']};
                color: {colors['TEXT']};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QLineEdit, QTextEdit {{
                background-color: {colors['SURFACE']};
                border: 1px solid {colors['GRID']};
                border-radius: 4px;
                padding: 5px;
            }}
            QPushButton {{
                background-color: {colors['PRIMARY']};
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                color: {colors['TEXT']};
            }}
            QPushButton:hover {{
                background-color: {colors['HOVER']};
            }}
            QTableWidget {{
                background-color: {colors['SURFACE']};
                alternate-background-color: {colors['ALTERNATE']};
                gridline-color: {colors['GRID']};
                selection-background-color: {colors['PRIMARY_DARK']};
                color: {colors['TEXT']};
            }}
            QHeaderView::section {{
                background-color: {colors['SURFACE']};
                border: 1px solid {colors['GRID']};
                padding: 4px;
            }}
            QProgressBar {{
                background-color: {colors['SURFACE']};
                border: 1px solid {colors['GRID']};
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {colors['PRIMARY']};
            }}
            QComboBox {{
                background-color: {colors['SURFACE']};
                border: 1px solid {colors['GRID']};
                border-radius: 4px;
                padding: 5px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;
                border-left: 1px solid {colors['GRID']};
            }}
            QLabel {{ color: {colors['TEXT']}; }}
            QTabWidget::pane {{ border: 1px solid {colors['GRID']}; }}
            QTabBar::tab {{
                background-color: {colors['SURFACE']};
                border: 1px solid {colors['GRID']};
                border-bottom-color: {colors['BACKGROUND']};
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px;
            }}
            QTabBar::tab:selected {{
                background-color: {colors['BACKGROUND']};
            }}
            QMenu {{
                background-color: {colors['BACKGROUND']};
                color: {colors['MENU_TEXT']};
                border: 1px solid {colors['GRID']};
                border-radius: 6px;
                padding: 4px;
                margin: 2px;
            }}
            QMenu::item {{
                background-color: {colors['SURFACE']};
                color: {colors['MENU_TEXT']};
                padding: 8px 28px;
                margin: 2px;
                border-radius: 3px;
            }}
            QMenu::item:selected {{
                background-color: {colors['PRIMARY_DARK']};
                color: {colors['MENU_TEXT']};
            }}
            QMenu::item:disabled {{
                color: {colors['NEUTRAL']};
            }}
            QMenu::separator {{
                height: 1px;
                background: {colors['GRID']};
                margin: 4px 8px;
            }}
        """
        self.setStyleSheet(stylesheet)

    def show_context_menu(self, position, tab_type):
        if tab_type == "download":
            table = self.table
            items = self.download_queue
        elif tab_type == "completed":
            table = self.completed_table
            items = self.completed_downloads
        else:
            return

        rows = [index.row() for index in table.selectionModel().selectedRows()]
        if not rows:
            return

        menu = QMenu()
        if tab_type == "download":
            start_action = QAction("شروع دانلود")
            start_action.triggered.connect(lambda: self.start_single_download_from_menu(rows[0]) if len(rows) == 1 else self.start_selected_downloads())
            menu.addAction(start_action)

            pause_action = QAction("مکث دانلود")
            pause_action.triggered.connect(lambda: self.pause_single_download(rows[0]) if len(rows) == 1 else None)
            pause_action.setEnabled(len(rows) == 1 and items[rows[0]]['status'] == "در حال دانلود...")
            menu.addAction(pause_action)

            resume_action = QAction("ادامه دانلود")
            resume_action.triggered.connect(lambda: self.resume_single_download(rows[0]) if len(rows) == 1 else None)
            resume_action.setEnabled(len(rows) == 1 and items[rows[0]]['status'] == "متوقف شده")
            menu.addAction(resume_action)

            cancel_single_action = QAction("لغو دانلود تکی")
            cancel_single_action.triggered.connect(lambda: self.cancel_single_download(rows[0]) if len(rows) == 1 else None)
            cancel_single_action.setEnabled(len(rows) == 1 and items[rows[0]]['status'] in ["در حال دانلود...", "متوقف شده"])
            menu.addAction(cancel_single_action)

            cancel_all_action = QAction("لغو تمام دانلودها")
            cancel_all_action.triggered.connect(self.cancel_all_downloads)
            menu.addAction(cancel_all_action)

            remove_action = QAction("حذف")
            remove_action.triggered.connect(self.remove_selected_items)
            menu.addAction(remove_action)

            copy_title = QAction("کپی عنوان")
            copy_title.triggered.connect(lambda: self.copy_selected_titles(rows))
            menu.addAction(copy_title)

            copy_url = QAction("کپی URL")
            copy_url.triggered.connect(lambda: self.copy_selected_urls(rows))
            menu.addAction(copy_url)

            download_thumb = QAction("دانلود تامنیل")
            download_thumb.triggered.connect(lambda: self.download_selected_thumbnails(rows))
            menu.addAction(download_thumb)

            export_selected = menu.addMenu("خروجی موارد انتخابی")
            export_selected.addAction("TXT").triggered.connect(lambda: self.export_selected_items('txt'))
            export_selected.addAction("JSON").triggered.connect(lambda: self.export_selected_items('json'))
            export_selected.addAction("CSV").triggered.connect(lambda: self.export_selected_items('csv'))

            open_folder = QAction("باز کردن پوشه ذخیره")
            open_folder.triggered.connect(self.open_save_folder)
            menu.addAction(open_folder)

            open_file_path = QAction("باز کردن مسیر ویدیو")
            open_file_path.triggered.connect(lambda: self.open_video_file_path(rows))
            if len(rows) == 1 and items[rows[0]].get('status') == "دانلود شده" and items[rows[0]].get('download_path'):
                open_file_path.setEnabled(True)
            else:
                open_file_path.setEnabled(False)
            menu.addAction(open_file_path)

            copy_all_urls = QAction("کپی تمام URLها")
            copy_all_urls.triggered.connect(self.copy_all_urls)
            menu.addAction(copy_all_urls)

        elif tab_type == "completed":
            copy_title = QAction("کپی عنوان")
            copy_title.triggered.connect(lambda: self.copy_selected_titles(rows, "completed"))
            menu.addAction(copy_title)

            copy_url = QAction("کپی URL")
            copy_url.triggered.connect(lambda: self.copy_selected_urls(rows, "completed"))
            menu.addAction(copy_url)

            export_selected = menu.addMenu("خروجی موارد انتخابی")
            export_selected.addAction("TXT").triggered.connect(lambda: self.export_selected_items('txt', "completed"))
            export_selected.addAction("JSON").triggered.connect(lambda: self.export_selected_items('json', "completed"))
            export_selected.addAction("CSV").triggered.connect(lambda: self.export_selected_items('csv', "completed"))

            open_folder = QAction("باز کردن پوشه ذخیره")
            open_folder.triggered.connect(self.open_save_folder)
            menu.addAction(open_folder)

            open_file_path = QAction("باز کردن مسیر ویدیو")
            open_file_path.triggered.connect(lambda: self.open_video_file_path(rows, "completed"))
            if len(rows) == 1 and items[rows[0]].get('download_path'):
                open_file_path.setEnabled(True)
            else:
                open_file_path.setEnabled(False)
            menu.addAction(open_file_path)

            copy_all_urls = QAction("کپی تمام URLها")
            copy_all_urls.triggered.connect(lambda: self.copy_all_urls("completed"))
            menu.addAction(copy_all_urls)

        menu.exec(table.viewport().mapToGlobal(position))

    def copy_selected_titles(self, rows, tab_type="download"):
        if not rows:
            return
        if tab_type == "download":
            titles = [self.download_queue[row]['title'] for row in rows if 0 <= row < len(self.download_queue)]
        else:
            titles = [self.completed_downloads[row]['title'] for row in rows if 0 <= row < len(self.completed_downloads)]
        if titles:
            QApplication.clipboard().setText("\n".join(titles))
            self.status_label.setText(f"{len(titles)} عنوان کپی شد.")

    def copy_selected_urls(self, rows, tab_type="download"):
        if not rows:
            return
        if tab_type == "download":
            urls = [self.download_queue[row]['url'] for row in rows if 0 <= row < len(self.download_queue)]
        else:
            urls = [self.completed_downloads[row]['url'] for row in rows if 0 <= row < len(self.completed_downloads)]
        if urls:
            QApplication.clipboard().setText("\n".join(urls))
            self.status_label.setText(f"{len(urls)} آدرس کپی شد.")

    def download_selected_thumbnails(self, rows):
        if not rows:
            return
        for row in rows:
            if 0 <= row < len(self.download_queue):
                item = self.download_queue[row]
                url = item.get('thumbnail_url')
                if not url:
                    self.log_message(f"تامنیل برای '{item['title']}' یافت نشد یا در دسترس نیست.")
                    continue
                
                safe_title = "".join(c for c in item['title'] if c.isalnum() or c in " ._()")
                file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره تامنیل", f"{safe_title}.jpg", "تصاویر (*.jpg *.png)")
                if file_path:
                    success = download_thumbnail(url, file_path)
                    if success:
                        self.log_message(f"تامنیل برای '{item['title']}' در {file_path} ذخیره شد.")
                    else:
                        self.log_message(f"خطا در دانلود تامنیل برای '{item['title']}'.")

    def copy_all_urls(self, tab_type="download"):
        if tab_type == "download":
            urls = "\n".join([item['url'] for item in self.download_queue])
        else:
            urls = "\n".join([item['url'] for item in self.completed_downloads])
        QApplication.clipboard().setText(urls)
        self.status_label.setText("تمامی آدرس‌ها در کلیپ‌بورد کپی شدند.")

    def open_save_folder(self):
        folder = self.settings.get("save_folder")
        if not os.path.exists(folder):
            QMessageBox.warning(self, "پوشه پیدا نشد", "پوشه ذخیره وجود ندارد.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            self.log_message(f"خطا در باز کردن پوشه: {e}")
            QMessageBox.critical(self, "خطا", f"خطا در باز کردن پوشه: {e}")

    def open_video_file_path(self, rows, tab_type="download"):
        if len(rows) != 1:
            QMessageBox.warning(self, "خطا", "لطفاً فقط یک ویدیو انتخاب کنید.")
            return
        row = rows[0]
        item = self.download_queue[row] if tab_type == "download" else self.completed_downloads[row]
        file_path = item.get('download_path')
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "خطا", "فایل ویدیویی یافت نشد.")
            return
        try:
            folder_path = os.path.dirname(file_path)
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder_path])
            else:
                subprocess.Popen(["xdg-open", folder_path])
            self.log_message(f"باز کردن مسیر فایل: {file_path}")
        except Exception as e:
            self.log_message(f"خطا در باز کردن مسیر فایل: {e}")
            QMessageBox.critical(self, "خطا", f"خطا در باز کردن مسیر فایل: {e}")

    def export_selected_items(self, file_type, tab_type="download"):
        if tab_type == "download":
            table = self.table
            items = self.download_queue
        else:
            table = self.completed_table
            items = self.completed_downloads

        selected_rows = [index.row() for index in table.selectionModel().selectedRows()]
        if not selected_rows:
            QMessageBox.warning(self, "هیچ انتخابی", "هیچ موردی انتخاب نشده است.")
            return
        
        selected_items = [items[row] for row in selected_rows]
        self._export_data_logic(selected_items, file_type)

    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.settings["save_folder"] = dialog.folder_label.text()
            self.settings["format"] = dialog.format_combo.currentText()
            self.settings["video_format"] = dialog.video_format_combo.currentText()
            self.settings["concurrency"] = dialog.concurrency_spin.value()
            self.settings["proxy"] = dialog.proxy_input.text()
            self.settings["subtitle_lang"] = dialog.subtitle_lang_combo.currentText()
            self.settings["theme"] = dialog.theme_combo.currentText()
            self.settings["clear_on_exit"] = dialog.clear_data_on_exit.isChecked()
            self.settings["delete_partial_on_cancel"] = dialog.delete_partial_on_cancel.isChecked()
            self.save_settings()
            self.apply_theme()
            self.log_message("تنظیمات ذخیره شد.")
            QMessageBox.information(self, "تنظیمات", "تنظیمات ذخیره شدند.")

    def load_settings(self):
        self.settings = load_json_file(CONFIG_PATH, {
            "window_size": [1200, 700],
            "save_folder": os.path.join(os.path.expanduser("~"), "Downloads"),
            "format": "ویدیو و صدا",
            "video_format": "mp4",
            "concurrency": 3,
            "proxy": "",
            "subtitle_lang": "هیچ",
            "theme": "Auto",
            "clear_on_exit": False,
            "delete_partial_on_cancel": False
        })

    def save_settings(self):
        self.settings["window_size"] = [self.width(), self.height()]
        save_json_file(CONFIG_PATH, self.settings)

    def load_queue(self):
        self.download_queue = load_json_file(QUEUE_PATH, [])
        for item in self.download_queue:
            item.setdefault('id', str(uuid.uuid4()))
            item.setdefault('subtitle_lang', self.settings.get("subtitle_lang", "هیچ"))
        self.log_message(f"صف دانلود بارگذاری شد: {len(self.download_queue)} مورد")

    def save_queue(self):
        save_json_file(QUEUE_PATH, self.download_queue)

    def import_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "وارد کردن فایل", "", "متن (*.txt);;CSV (*.csv)")
        if not file_path:
            return
        
        urls = []
        if file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip().startswith('http')]
        elif file_path.endswith('.csv'):
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                urls = [row[0] for row in reader if row and row[0].strip().startswith('http')]
        
        if urls:
            self.ui_update_signal.emit(f"در حال وارد کردن {len(urls)} آدرس...", False)
            self.thread_pool.submit(self._fetch_and_add_list, urls)
        else:
            QMessageBox.warning(self, "فایل خالی", "فایل انتخاب شده حاوی آدرس معتبری نیست.")

    def _export_data_logic(self, data_list, file_type):
        dialog = SaveDialog(self)
        if not dialog.exec():
            return

        fields = dialog.get_selected_fields()
        if not fields:
            QMessageBox.warning(self, "انتخابی صورت نگرفت", "حداقل یک فیلد انتخاب کنید.")
            return

        default_filename = "youtube_downloader_export"
        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره فایل", f"{default_filename}.{file_type}", f"فایل {file_type.upper()} (*.{file_type})")
        if not file_path:
            return
        
        try:
            if file_type == 'txt':
                with open(file_path, 'w', encoding='utf-8') as f:
                    for item in data_list:
                        for field in fields:
                            f.write(f"{field}: {item.get(self._get_field_key(field), 'نامشخص')}\n")
                        f.write("--------------------\n")
            elif file_type == 'json':
                data_to_save = [{self._get_field_key(field): item.get(self._get_field_key(field), 'نامشخص') for field in fields} for item in data_list]
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, indent=4, ensure_ascii=False)
            elif file_type == 'csv':
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(fields)
                    for item in data_list:
                        row_data = [item.get(self._get_field_key(field), 'نامشخص') for field in fields]
                        writer.writerow(row_data)
            self.log_message(f"اطلاعات در {os.path.basename(file_path)} ذخیره شد.")
        except IOError as e:
            self.log_message(f"خطا در ذخیره فایل: {e}")
            QMessageBox.critical(self, "خطا", f"خطا در ذخیره فایل: {e}")

    def export_to_file(self, file_type):
        if not self.download_queue:
            QMessageBox.warning(self, "صف خالی است", "هیچ موردی در صف دانلود نیست.")
            return
        self._export_data_logic(self.download_queue, file_type)

    def export_completed_list(self):
        if not self.completed_downloads:
            QMessageBox.warning(self, "لیست خالی است", "هیچ موردی در لیست دانلود شده‌ها نیست.")
            return
        file_type, _ = QInputDialog.getItem(self, "انتخاب فرمت", "فرمت فایل را انتخاب کنید:", ["TXT", "JSON", "CSV"], 0, False)
        if file_type:
            self._export_data_logic(self.completed_downloads, file_type.lower())

    def _get_field_key(self, field_name):
        translation_map = {
            "عنوان": "title", "URL": "url", "حجم": "filesize_str",
            "تعداد بازدید": "view_count", "تاریخ آپلود": "upload_date",
            "کیفیت": "quality", "مسیر ذخیره": "download_path",
            "لینک تامنیل": "thumbnail_url"
        }
        return translation_map.get(field_name, field_name.lower().replace(" ", "_"))

    def clear_queue(self):
        if self.active_downloads:
            QMessageBox.warning(self, "عملیات ناموفق", "لطفاً ابتدا تمام دانلودهای فعال را لغو کنید.")
            return
        self.table.setRowCount(0)
        self.download_queue = []
        self.id_to_row = {}
        self.save_queue()
        self.status_label.setText("صف پاک شد.")
        self.log_message("صف دانلود پاک شد.")

    def add_to_queue(self):
        url = self.url_input.text().strip()
        if not url:
            return
        self.add_btn.setEnabled(False)
        self.cancel_add_btn.setEnabled(True)
        self.fetch_cancelled = False
        self.status_label.setText("در حال دریافت اطلاعات...")
        self.thread_pool.submit(self._fetch_and_add, url)

    def cancel_add_to_queue(self):
        self.fetch_cancelled = True
        self.status_label.setText("اضافه کردن لغو شد.")
        self.add_btn.setEnabled(True)
        self.cancel_add_btn.setEnabled(False)
        self.url_input.clear()

    def _fetch_and_add(self, url):
        yt_path = get_yt_dlp_path()
        if not yt_path:
            self.ui_update_signal.emit("خطا: yt-dlp در دسترس نیست.", True)
            return
        try:
            # Use --flat-playlist for playlists
            cmd = [yt_path, "--flat-playlist", "-J", url]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = json.loads(result.stdout.strip()) if result.stdout.strip() else {}

            if self.fetch_cancelled:
                return

            if 'entries' in info:
                entries = info.get('entries', [])
                batch_size = 100  # افزایش batch size برای کاهش فراخوانی UI
                for i in range(0, len(entries), batch_size):
                    if self.fetch_cancelled:
                        return
                    batch = entries[i:i+batch_size]
                    for entry in batch:
                        if self.fetch_cancelled:
                            return
                        if entry and entry.get('url'):
                            video_id_or_url = entry.get('url', '')
                            if video_id_or_url.startswith('http'):
                                full_url = video_id_or_url
                            else:
                                full_url = f"https://www.youtube.com/watch?v={video_id_or_url}"
                            entry['webpage_url'] = full_url
                            self.video_info_loaded.emit(-1, entry)
                    time.sleep(0.5)  # افزایش sleep برای جلوگیری از freeze UI
            else:
                info['webpage_url'] = url
                self.video_info_loaded.emit(-1, info)
        except Exception as e:
            if not self.fetch_cancelled:
                self.ui_update_signal.emit(f"خطا در دریافت اطلاعات: {e}", True)
                self.log_message(f"خطا در دریافت اطلاعات: {e}")
        finally:
            self.ui_update_signal.emit("آماده.", True)
            QMetaObject.invokeMethod(self, "reset_add_buttons", Qt.QueuedConnection)

    def reset_add_buttons(self):
        self.add_btn.setEnabled(True)
        self.cancel_add_btn.setEnabled(False)
        self.url_input.clear()

    def update_ui_from_thread(self, status_text, enable_button):
        self.status_label.setText(status_text)
        if enable_button:
            self.add_btn.setEnabled(True)
            self.cancel_add_btn.setEnabled(False)

    def _add_to_table_from_thread(self, row, video_info):
        url = video_info.get("webpage_url", video_info.get("url", ""))
        if any(item['url'] == url for item in self.download_queue):
            self.log_message(f"URL تکراری: {url}")
            return

        filesize = video_info.get('filesize_approx', video_info.get('filesize'))
        filesize_str = format_file_size(filesize)
        duration_str = format_duration(video_info.get('duration'))
        thumbnail_url = video_info.get('thumbnail') or video_info.get('thumbnails', [{}])[-1].get('url', '')

        item_id = str(uuid.uuid4())
        
        item = {
            "id": item_id,
            "title": video_info.get("title", "نامشخص"),
            "url": url,
            "filesize_str": filesize_str,
            "duration_str": duration_str,
            "view_count": video_info.get("view_count", 0),
            "upload_date": video_info.get("upload_date", ""),
            "status": "در صف",
            "quality": self.settings.get("quality", "بهترین"),
            "format": self.settings.get("format", "ویدیو و صدا"),
            "video_format": self.settings.get("video_format", "mp4"),
            "subtitle_lang": self.settings.get("subtitle_lang", "هیچ"),
            "download_path": None,
            "thumbnail_url": thumbnail_url,
            "downloaded_size": "0 B"  # مقدار اولیه حجم دانلود شده
        }

        ext = 'mp3' if item["format"] == "فقط صدا" else item["video_format"]
        exists, path = check_file_exists(self.settings.get("save_folder"), item['title'], ext)
        if exists:
            item['status'] = "دانلود شده"
            item['download_path'] = path
            self.completed_downloads.append(item)
            self.update_completed_table_row(self.completed_table.rowCount(), item)
        else:
            partial_exists, part_path = check_partial_file(self.settings.get("save_folder"), item['title'], ext)
            if partial_exists:
                item['status'] = "متوقف شده"
                # تخمین حجم دانلود شده از فایل part
                if os.path.exists(part_path):
                    item['downloaded_size'] = format_file_size(os.path.getsize(part_path))
            self.download_queue.append(item)
            self.id_to_row[item_id] = self.table.rowCount()
            self.table.setRowCount(self.table.rowCount() + 1)
            self.update_table_row(self.table.rowCount() - 1, item)
        
        self.save_queue()
        self.status_label.setText(f"'{item['title']}' به صف اضافه شد.")
        self.log_message(f"اضافه شدن به صف: {item['title']}")

    def _fetch_and_add_list(self, urls):
        yt_path = get_yt_dlp_path()
        if not yt_path:
            self.ui_update_signal.emit("خطا: yt-dlp در دسترس نیست.", True)
            return
        batch_size = 100  # افزایش batch size
        for i in range(0, len(urls), batch_size):
            if self.fetch_cancelled:
                return
            batch = urls[i:i+batch_size]
            for url in batch:
                if self.fetch_cancelled:
                    return
                try:
                    cmd = [yt_path, "--flat-playlist", "-J", url]
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    info = json.loads(result.stdout.strip()) if result.stdout.strip() else {}
                    self.video_info_loaded.emit(-1, info)
                except Exception as e:
                    self.log_message(f"خطا در دریافت اطلاعات URL {url}: {e}")
                time.sleep(0.1)  # کاهش sleep برای لیست‌های کوچک
        self.ui_update_signal.emit("وارد کردن آدرس‌ها به پایان رسید.", True)

    def restore_queue_to_table(self):
        self.table.setRowCount(len(self.download_queue))
        for row, item in enumerate(self.download_queue):
            self.id_to_row[item['id']] = row
            self.update_table_row(row, item)
        self.load_visible_thumbnails()

    def update_table_row(self, row, item):
        self.table.setItem(row, 0, QTableWidgetItem(item.get("title")))
        self.table.setItem(row, 1, QTableWidgetItem(item.get("url")))
        self.table.setItem(row, 2, QTableWidgetItem(item.get("filesize_str")))
        self.table.setItem(row, 3, QTableWidgetItem(item.get("duration_str")))
        
        quality_combo = QComboBox()
        quality_combo.addItems(QUALITY_OPTIONS)
        quality_combo.setCurrentText(item.get("quality", "بهترین"))
        quality_combo.currentTextChanged.connect(lambda text: self._update_item_field(row, 'quality', text))
        self.table.setCellWidget(row, 4, quality_combo)
        
        format_combo = QComboBox()
        format_combo.addItems(FORMAT_OPTIONS)
        format_combo.setCurrentText(item.get("format", self.settings.get("format", "ویدیو و صدا")))
        format_combo.currentTextChanged.connect(lambda text: self._update_item_field(row, 'format', text))
        self.table.setCellWidget(row, 5, format_combo)
        
        subtitle_combo = QComboBox()
        subtitle_combo.addItems(SUBTITLE_LANGS)
        subtitle_combo.setCurrentText(item.get("subtitle_lang", "هیچ"))
        subtitle_combo.currentTextChanged.connect(lambda text: self._update_item_field(row, 'subtitle_lang', text))
        self.table.setCellWidget(row, 6, subtitle_combo)
        
        self.table.setItem(row, 7, QTableWidgetItem(item.get("status")))
        self.table.setCellWidget(row, 8, QProgressBar())
        self.table.setItem(row, 9, QTableWidgetItem(item.get("downloaded_size", "0 B")))  # ستون حجم دانلود شده
        self.table.setItem(row, 10, QTableWidgetItem(""))  # سرعت
        self.table.setItem(row, 11, QTableWidgetItem(""))  # زمان باقی‌مانده

    def _update_item_field(self, row, field, value):
        if 0 <= row < len(self.download_queue):
            self.download_queue[row][field] = value
            self.save_queue()

    def filter_table(self, text):
        for row in range(self.table.rowCount()):
            title_item = self.table.item(row, 0)
            url_item = self.table.item(row, 1)
            match = (
                (title_item and text.lower() in title_item.text().lower()) or
                (url_item and text.lower() in url_item.text().lower())
            )
            self.table.setRowHidden(row, not match)

    def start_downloads(self):
        if not self.check_dependencies(silent=False):
            return
        self.downloading_all = True
        self.start_download_btn.setEnabled(False)
        self.cancel_download_btn.setEnabled(True)
        self.status_label.setText("شروع دانلودها...")
        self.log_message("شروع دانلود تمام موارد در صف.")
        self._start_next_downloads()

    def start_selected_downloads(self):
        if not self.check_dependencies(silent=False):
            return
        self.downloading_all = False
        selected_rows = [index.row() for index in self.table.selectionModel().selectedRows()]
        for row in selected_rows:
            item = self.download_queue[row]
            if item['status'] in ["در صف", "خطا", "لغو شده", "متوقف شده"]:
                self._start_single_download(row, item, resume=item['status'] == "متوقف شده")
                self.log_message(f"شروع دانلود انتخاب شده: {item['title']}")

    def _start_next_downloads(self):
        concurrency = self.settings.get("concurrency", 3)
        while len(self.active_downloads) < concurrency:
            next_item_tuple = next(((i, item) for i, item in enumerate(self.download_queue) if item['status'] == "در صف" or item['status'] == "متوقف شده"), None)
            if not next_item_tuple:
                break
            row, item = next_item_tuple
            self._start_single_download(row, item, resume=item['status'] == "متوقف شده")

    def _start_single_download(self, row, item, resume=False):
        if item['status'] == "دانلود شده":
            return
        
        item['quality'] = self.table.cellWidget(row, 4).currentText()
        item['format'] = self.table.cellWidget(row, 5).currentText()
        item['subtitle_lang'] = self.table.cellWidget(row, 6).currentText()
        self.save_queue()
        
        item['status'] = "در حال دانلود..."
        self.table.setItem(row, 7, QTableWidgetItem("در حال دانلود..."))
        progress_bar = self.table.cellWidget(row, 8)
        if progress_bar:
            if not resume:
                progress_bar.setValue(0)

        safe_title = "".join(c for c in item['title'] if c.isalnum() or c in " ._()")
        ydl_opts = {
            'outtmpl': {'default': os.path.join(self.settings.get("save_folder"), f'{safe_title}.%(ext)s')},
            'retries': 10,
            'fragment_retries': 10,
            'quiet': False,
            'continuedl': True,
            'nooverwrites': False  # اجازه بازنویسی فایل‌های ناقص
        }
        if self.settings.get("proxy"):
            ydl_opts['proxy'] = self.settings["proxy"]
        
        if item['format'] == "فقط صدا":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]
        else:
            quality_str = item['quality']
            video_format = item.get('video_format', self.settings.get("video_format", "mp4"))
            if quality_str == "بهترین":
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
            elif quality_str == "بدترین":
                ydl_opts['format'] = 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]'
            else:
                res = quality_str.replace("p", "")
                ydl_opts['format'] = f'bestvideo[ext=mp4][height<={res}]+bestaudio[ext=m4a]/best[ext=mp4][height<={res}]'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegVideoConvertor', 'preferedformat': video_format}]

        subtitle_lang = item['subtitle_lang']
        if subtitle_lang != "هیچ":
            lang_code = subtitle_lang.split(' (')[1][:-1]
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] = [lang_code]
            ydl_opts['postprocessors'].append({'key': 'FFmpegSubtitlesConvertor', 'format': 'srt'})

        if not self.yt_dlp_path or not self.ffmpeg_path:
            self.log_message("ابزارهای لازم (yt-dlp یا ffmpeg) در دسترس نیستند.")
            item['status'] = "خطا"
            self.table.setItem(row, 7, QTableWidgetItem("خطا"))
            return

        downloader = DownloaderThread(item['id'], item['url'], ydl_opts, self.yt_dlp_path, self.ffmpeg_path)
        downloader.download_progress.connect(self.on_download_progress)
        downloader.postprocess_progress.connect(self.on_postprocess_progress)
        downloader.download_finished.connect(self.on_download_finished)
        downloader.download_error.connect(self.on_download_error)
        downloader.download_cancelled.connect(self.on_download_cancelled)
        downloader.download_step.connect(self.on_download_step)
        downloader.log_line.connect(self.log_signal)
        self.active_downloads.append(downloader)
        downloader.start()
        self.progress_emit_counter[item['id']] = 0  # Reset counter

    def on_download_step(self, item_id, step_msg):
        row = self.id_to_row.get(item_id)
        if row is not None:
            self.log_message(f"[{self.download_queue[row]['title']}] {step_msg}")

    def on_download_progress(self, d):
        row = self.id_to_row.get(d['id'])
        if row is None or row >= self.table.rowCount():
            return

        if d['status'] == 'downloading':
            try:
                percent = float(d.get('_percent_str', '0%').strip().replace('%', ''))
                downloaded_str = d.get('downloaded_bytes', '0 B')
                speed_str = format_speed(d.get('speed'))
                eta_str = format_eta(d.get('eta'))

                # Rate-limit emits to every 5% or 1 second to prevent UI freeze
                counter = self.progress_emit_counter.get(d['id'], 0) + 1
                self.progress_emit_counter[d['id']] = counter
                if counter % 5 == 0 or percent % 5 == 0:  # Emit every 5 updates or 5%
                    self.update_progress.emit(d['id'], percent, downloaded_str, speed_str, eta_str)
            except (ValueError, AttributeError):
                pass

    def _update_progress_ui(self, item_id, percent, downloaded_str, speed_str, eta_str):
        row = self.id_to_row.get(item_id)
        if row is None or row >= self.table.rowCount():
            return
        progress_bar = self.table.cellWidget(row, 8)
        if progress_bar:
            progress_bar.setValue(int(percent))
        self.table.setItem(row, 9, QTableWidgetItem(downloaded_str))  # حجم دانلود شده
        self.table.setItem(row, 10, QTableWidgetItem(speed_str))  # سرعت
        self.table.setItem(row, 11, QTableWidgetItem(eta_str))  # زمان باقی‌مانده
        # به‌روزرسانی item در queue برای حفظ حجم دانلود شده
        if 0 <= row < len(self.download_queue):
            self.download_queue[row]['downloaded_size'] = downloaded_str
        self.save_queue()  # ذخیره فوری برای حفظ داده
        self.log_message(f"پیشرفت دانلود [{self.download_queue[row]['title']}]: {percent:.2f}% - حجم: {downloaded_str} - سرعت: {speed_str} - باقی‌مانده: {eta_str}")

    def on_postprocess_progress(self, d):
        row = self.id_to_row.get(d['id'])
        if row is None or row >= self.table.rowCount():
            return
        progress_bar = self.table.cellWidget(row, 8)
        if progress_bar:
            value = 100 if d['status'] == 'finished' else 50
            progress_bar.setValue(value)
            self.table.setItem(row, 10, QTableWidgetItem(""))  # پاک کردن سرعت
            self.table.setItem(row, 11, QTableWidgetItem(""))  # پاک کردن ETA
            self.log_message(f"پردازش پس از دانلود [{d.get('filename', 'نامشخص')}]: وضعیت {d['status']}")

    def on_download_finished(self, info_dict):
        item_id = info_dict['id']
        thread_index = self._find_thread_by_id(item_id)
        if thread_index != -1:
            self.active_downloads.pop(thread_index)
        
        row = self.id_to_row.get(item_id)
        if row is not None:
            item = self.download_queue.pop(row)
            item['status'] = "دانلود شده"
            item['download_path'] = info_dict.get('filepath')
            # حفظ حجم نهایی دانلود شده
            item['downloaded_size'] = item.get('filesize_str', 'نامشخص')
            self.completed_downloads.append(item)
            self.table.removeRow(row)
            self._update_id_to_row_map()
            self.update_completed_table_row(self.completed_table.rowCount(), item)
            self.log_message(f"دانلود پایان یافت: {item['title']} - مسیر: {item['download_path']}")

        self.save_queue()
        self.check_all_finished()
        if self.downloading_all:
            self._start_next_downloads()

    def update_completed_table_row(self, row, item):
        self.completed_table.setRowCount(row + 1)
        self.completed_table.setItem(row, 0, QTableWidgetItem(item.get("title")))
        self.completed_table.setItem(row, 1, QTableWidgetItem(item.get("url")))
        self.completed_table.setItem(row, 2, QTableWidgetItem(item.get("filesize_str")))
        self.completed_table.setItem(row, 3, QTableWidgetItem(item.get("duration_str")))
        self.completed_table.setItem(row, 4, QTableWidgetItem(item.get("quality")))
        self.completed_table.setItem(row, 5, QTableWidgetItem(item.get("status")))
        date_str = item.get('upload_date', '')
        if date_str:
            self.completed_table.setItem(row, 6, QTableWidgetItem(f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:]}"))
        self.completed_table.setItem(row, 7, QTableWidgetItem(item.get("download_path")))

    def on_download_error(self, error_msg, item_id):
        self._handle_download_end(item_id, "خطا", error_msg, is_pause=False)

    def on_download_cancelled(self, item_id):
        row = self.id_to_row.get(item_id)
        if row is not None:
            item = self.download_queue[row]
            thread = next((t for t in self.active_downloads if t.id == item_id), None)
            if thread:
                if thread.is_paused:
                    self._handle_download_end(item_id, "متوقف شده", "دانلود متوقف شد.", is_pause=True)
                else:
                    self._handle_download_end(item_id, "لغو شده", "دانلود لغو شد.", is_pause=False)

    def _handle_download_end(self, item_id, status, message, is_pause=False):
        thread_index = self._find_thread_by_id(item_id)
        if thread_index != -1:
            thread = self.active_downloads.pop(thread_index)
            if not thread.wait(timeout=5):  # Wait with timeout to prevent hang
                thread.terminate()
                thread.wait()

        row = self.id_to_row.get(item_id)
        if row is not None and row < self.table.rowCount():
            item = self.download_queue[row]
            self.table.setItem(row, 7, QTableWidgetItem(status))
            self.table.setItem(row, 10, QTableWidgetItem(""))  # Clear speed
            self.table.setItem(row, 11, QTableWidgetItem(""))  # Clear ETA
            # حفظ حجم دانلود شده در item و سلول (حتی پس از لغو)
            downloaded_item = self.table.item(row, 9)
            if downloaded_item:
                item['downloaded_size'] = downloaded_item.text()
            item['status'] = status
            if not is_pause and status == "لغو شده" and self.settings.get("delete_partial_on_cancel", False):
                ext = 'mp3' if item.get('format') == "فقط صدا" else item.get('video_format', 'mp4')
                delete_partial_files(self.settings.get("save_folder"), item['title'], ext)
            self.log_message(f"'{item['title']}': {message} - وضعیت: {status}")
        
        self.save_queue()
        self.check_all_finished()
        if self.downloading_all:
            self._start_next_downloads()

    def _find_thread_by_id(self, item_id):
        return next((i for i, thread in enumerate(self.active_downloads) if thread.id == item_id), -1)

    def remove_selected_items(self):
        selected_rows = sorted([index.row() for index in self.table.selectionModel().selectedRows()], reverse=True)
        for row in selected_rows:
            self.remove_single_item(row)
            self.log_message(f"حذف مورد از صف: ردیف {row}")

    def remove_single_item(self, row):
        if not (0 <= row < self.table.rowCount()):
            return
        item = self.download_queue[row]
        self.cancel_single_download(row)
        del self.id_to_row[item['id']]
        del self.download_queue[row]
        self.table.removeRow(row)
        self._update_id_to_row_map()
        self.save_queue()

    def _update_id_to_row_map(self):
        self.id_to_row = {item['id']: i for i, item in enumerate(self.download_queue)}

    def pause_single_download(self, row):
        if 0 <= row < len(self.download_queue):
            item = self.download_queue[row]
            thread_index = self._find_thread_by_id(item['id'])
            if thread_index != -1:
                self.active_downloads[thread_index].is_paused = True
                if not self.active_downloads[thread_index].wait(timeout=5):
                    self.active_downloads[thread_index].terminate()
                    self.active_downloads[thread_index].wait()
                self.log_message(f"مکث دانلود: {item['title']}")
                self._handle_download_end(item['id'], "متوقف شده", "دانلود مکث شد.", is_pause=True)

    def resume_single_download(self, row):
        if 0 <= row < len(self.download_queue):
            item = self.download_queue[row]
            if item['status'] == "متوقف شده":
                self._start_single_download(row, item, resume=True)
                self.log_message(f"ادامه دانلود: {item['title']}")

    def cancel_single_download(self, row):
        if 0 <= row < len(self.download_queue):
            item = self.download_queue[row]
            thread_index = self._find_thread_by_id(item['id'])
            if thread_index != -1:
                self.active_downloads[thread_index].is_cancelled = True
                if not self.active_downloads[thread_index].wait(timeout=5):
                    self.active_downloads[thread_index].terminate()
                    self.active_downloads[thread_index].wait()
                self.log_message(f"لغو دانلود تکی: {item['title']}")

    def start_single_download_from_menu(self, row):
        if 0 <= row < len(self.download_queue):
            self.downloading_all = False
            item = self.download_queue[row]
            if item['status'] in ["در صف", "خطا", "لغو شده", "متوقف شده"]:
                self._start_single_download(row, item, resume=item['status'] == "متوقف شده")
                self.log_message(f"شروع دانلود از منو: {item['title']}")

    def cancel_all_downloads(self):
        for thread in list(self.active_downloads):
            thread.is_cancelled = True
            if not thread.wait(timeout=5):
                thread.terminate()
                thread.wait()
        self.downloading_all = False
        self.log_message("لغو تمام دانلودها.")
        self.check_all_finished()

    def check_all_finished(self):
        if not self.active_downloads and not any(q['status'] == "در حال دانلود..." for q in self.download_queue):
            self.status_label.setText("عملیات دانلود به پایان رسید.")
            self.cancel_download_btn.setEnabled(False)
            self.start_download_btn.setEnabled(True)
            self.downloading_all = False
            self.log_message("تمام عملیات دانلود به پایان رسید.")

    def check_dependencies(self, silent=True):
        self.yt_dlp_path = get_yt_dlp_path()
        self.ffmpeg_path = get_ffmpeg_path()
        self.yt_dlp_version = get_yt_dlp_version()
        self.ffmpeg_version = get_ffmpeg_version()

        if not self.yt_dlp_path:
            if not silent:
                QMessageBox.critical(self, "وابستگی", "yt-dlp یافت نشد و دانلود ناموفق بود.")
            return False
        if not self.ffmpeg_path:
            if not silent:
                QMessageBox.warning(self, "وابستگی", "ffmpeg یافت نشد و دانلود ناموفق بود.")
            return False
        return True

    def _refresh_ui(self):
        for row in range(self.table.rowCount()):
            progress_bar = self.table.cellWidget(row, 8)
            item = self.download_queue[row]
            if progress_bar and progress_bar.value() == 0 and item['status'] != "در حال دانلود...":
                self.table.setItem(row, 10, QTableWidgetItem(""))  # Clear speed
                self.table.setItem(row, 11, QTableWidgetItem(""))  # Clear ETA
                # حجم دانلود شده حفظ می‌شود و پاک نمی‌شود

    def closeEvent(self, event):
        self.cancel_all_downloads()
        self.ui_timer.stop()
        self.save_settings()
        self.thread_pool.shutdown(wait=True)
        if self.settings.get("clear_on_exit", False):
            if os.path.exists(QUEUE_PATH):
                os.remove(QUEUE_PATH)
                self.log_message("صف دانلود هنگام خروج پاک شد.")
        event.accept()

    def load_visible_thumbnails(self):
        pass  # اگر لازم شد، اینجا پیاده‌سازی شود

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("icon.ico")))
    ex = App()
    ex.setWindowIcon(QIcon(resource_path("icon.ico")))
    ex.show()
    sys.exit(app.exec())
