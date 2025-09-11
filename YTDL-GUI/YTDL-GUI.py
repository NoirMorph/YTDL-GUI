# -*- coding: utf-8 -*-
"""
دانلودکننده یوتیوب (نسخه اصلاح‌شده و تمیز با UI بهبودیافته و تم تیره)
این نسخه تمام خطاهای مربوط به thread در PyQt6 را برطرف کرده و قابلیت‌های زیر را اضافه می‌کند:
- انتخاب جداگانه کیفیت برای هر ویدیو
- نمایش لینک ویدیو در جدول
- قابلیت حذف تکی ویدیوها
- منوی راست‌کلیک پیشرفته با قابلیت باز کردن مسیر فایل
- رفع کامل خطاهای QObject::setParent و QObject::Cannot create children
- قابلیت پاک شدن اطلاعات پس از خروج
- قابلیت ذخیره اطلاعات در فایل های txt, json, csv (برای صف دانلود، دانلود شده‌ها و موارد انتخاب شده)
- انتخاب چندین ویدیو (تکی و چندتایی)
- جستجو و فیلتر جدول
- نمایش مراحل عملیات و مدیریت بهتر خطاها
- نمایش میزان دانلود و محل ذخیره ویدیو
- چک کردن وجود فایل دانلود شده قبلی
- ریسایز سلول‌ها
- نمایش عملیات‌ها و خطاها داخل برنامه بدون کرش
- قابلیت لغو عملیات
- گزینه‌های بیشتر در منوی راست‌کلیک
- هنگام بستن برنامه، غیرفعال کردن عملیات‌ها و انتقال دانلودهای فعال به تب جدید
- پروگرس بار برای دانلود و تبدیل فایل
- دکمه لغو برای هر عملیات جداگانه
- تب دانلود تکی (بدون هنگ کردن) با نمایش اطلاعات و دانلود thumbnail
- قابلیت انتخاب فرمت خروجی برای هر ویدیو
- قابلیت کپی و ذخیره اطلاعات ویدیوهای انتخاب شده از راست‌کلیک
- بهبود: دانلود خودکار ffmpeg اگر نصب نبود برای پشتیبانی از تبدیل فرمت

بهبودهای UI:
- استفاده از QStyleSheet برای ظاهر مدرن و تمیز با تم تیره
- اضافه کردن حاشیه‌ها، فونت‌ها و رنگ‌های هماهنگ
- بهبود لی‌آوت‌ها برای پاسخگویی بهتر
- اضافه کردن tooltip برای عناصر
- آیکون برنامه اضافه شده (فرض بر وجود فایل icon.png در دایرکتوری جاری)
- بهبود بیشتر: اضافه کردن border-radius, hover effects, alternate row colors در جدول، bold labels, framed thumbnail
"""
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
import hashlib
import zipfile
import tarfile
import platform
import shutil

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QComboBox,
    QMessageBox, QProgressBar, QSpinBox, QDialog, QFormLayout, QMenuBar, QMenu,
    QCheckBox, QTabWidget, QTextEdit, QInputDialog, QAbstractItemView
)
from PyQt6.QtGui import QPixmap, QAction, QIcon, QFont
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMetaObject, QEvent

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import yt_dlp

# ---------------- Color Variables for Dark Theme ----------------
COLOR_PRIMARY = "#5682B1"  # blue for primary actions
COLOR_SECONDARY = "#739EC9"  # Teal for secondary actions
COLOR_DANGER = "#CF6679"  # Red for danger actions
COLOR_NEUTRAL = "#B3B3B3"  # Light gray for neutral
COLOR_BACKGROUND = "#121212"  # Dark background
COLOR_TEXT = "#FFFFFF"  # White text
COLOR_ACCENT = "#44444E"  # Yellow accent
COLOR_SURFACE = "#1E1E1E"  # Slightly lighter dark for surfaces
COLOR_GRID = "#333333"  # Dark grid lines
COLOR_HOVER = "#154D71"  # Dark blue for hover
COLOR_ALTERNATE = "#2A2A2A"  # Alternate row color

# ---------------- Constants ----------------
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".youtube_downloader_config.json")
QUEUE_PATH = os.path.join(os.path.expanduser("~"), ".youtube_downloader_queue.json")
THUMB_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".youtube_downloader_thumbs")
FFMPEG_DIR = os.path.join(os.path.expanduser("~"), ".ffmpeg_bin")
QUALITY_OPTIONS = ["بهترین", "بدترین", "1080p", "720p", "480p", "360p", "144p"]
FORMAT_OPTIONS = ["ویدیو و صدا", "فقط صدا"]
VIDEO_FORMAT_OPTIONS = ["mp4", "mkv", "mov", "avi", "webm"]
SUBTITLE_LANGS = ["هیچ", "انگلیسی (en)", "فارسی (fa)"]

# ---------------- Helper Functions ----------------

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(os.path.dirname(__file__))
    full_path = os.path.join(base_path, relative_path)
    logging.info(f"تلاش برای دسترسی به فایل: {full_path}")
    if not os.path.exists(full_path):
        logging.error(f"فایل {full_path} یافت نشد.")
    return full_path

def download_ffmpeg():
    """دانلود و استخراج ffmpeg بسته به سیستم عامل."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "windows":
        url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        file_ext = ".zip"
    elif system == "darwin":  # macOS
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
    
    download_path = os.path.join(FFMPEG_DIR, f"ffmpeg{file_ext}")
    
    os.makedirs(FFMPEG_DIR, exist_ok=True)
    
    # دانلود فایل
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(download_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    else:
        raise IOError("خطا در دانلود ffmpeg.")
    
    # استخراج
    if file_ext == ".zip":
        with zipfile.ZipFile(download_path, 'r') as zip_ref:
            zip_ref.extractall(FFMPEG_DIR)
    elif file_ext == ".tar.xz":
        with tarfile.open(download_path, 'r:xz') as tar_ref:
            tar_ref.extractall(FFMPEG_DIR)
    
    # پیدا کردن و کپی باینری‌ها
    for root, dirs, files in os.walk(FFMPEG_DIR):
        for file in files:
            if file in ["ffmpeg", "ffmpeg.exe", "ffprobe", "ffprobe.exe", "ffplay", "ffplay.exe"]:
                shutil.copy(os.path.join(root, file), FFMPEG_DIR)
    
    os.remove(download_path)
    return os.path.join(FFMPEG_DIR, "ffmpeg" if system != "windows" else "ffmpeg.exe")

def get_ffmpeg_path():
    system = platform.system().lower()
    ffmpeg_name = "ffmpeg.exe" if system == "windows" else "ffmpeg"
    ffmpeg_path = resource_path(os.path.join("ffmpeg_bin", ffmpeg_name))
    
    logging.info(f"تلاش برای دسترسی به ffmpeg در مسیر: {ffmpeg_path}")
    
    if os.path.exists(ffmpeg_path):
        if system != "windows":
            try:
                os.chmod(ffmpeg_path, 0o755)
                logging.info(f"مجوزهای ffmpeg تنظیم شد: {ffmpeg_path}")
            except OSError as e:
                logging.error(f"خطا در تنظیم مجوزهای ffmpeg: {e}")
                QMessageBox.critical(None, "خطا", f"خطا در تنظیم مجوزهای ffmpeg: {e}")
                return None
        logging.info(f"ffmpeg با موفقیت یافت شد: {ffmpeg_path}")
        return ffmpeg_path
    
    logging.error("ffmpeg در پروژه یافت نشد. لطفاً فایل‌های باینری ffmpeg را در پوشه ffmpeg_bin قرار دهید.")
    QMessageBox.critical(None, "خطا", "ffmpeg یافت نشد. لطفاً اطمینان حاصل کنید که فایل‌های باینری ffmpeg در پوشه ffmpeg_bin موجود باشند.")
    return None

def get_yt_dlp_version():
    """نسخه yt-dlp را بررسی می‌کند و برمی‌گرداند."""
    try:
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def get_ffmpeg_version():
    """بررسی می‌کند که آیا ffmpeg نصب است."""
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        return None
    try:
        result = subprocess.run([ffmpeg_path, '-version'], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return "installed"
        return None
    except FileNotFoundError:
        return None

def load_json_file(file_path, default_data=None):
    """یک فایل JSON را بارگذاری می‌کند یا داده پیش‌فرض را برمی‌گرداند."""
    if not os.path.exists(file_path):
        return default_data if default_data is not None else {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, (dict, list)):
            raise ValueError("Invalid JSON structure")
        return data
    except (json.JSONDecodeError, ValueError) as e:
        logging.error(f"Invalid JSON in {file_path}: {e}")
        QMessageBox.warning(None, "خطای فایل", f"فایل {file_path} خراب است. داده پیش‌فرض استفاده می‌شود.")
        return default_data if default_data is not None else {}

def save_json_file(file_path, data):
    """داده‌ها را در یک فایل JSON ذخیره می‌کند."""
    try:
        backup_path = file_path + ".bak"
        if os.path.exists(file_path):
            os.replace(file_path, backup_path)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        logging.error(f"Failed to save file {file_path}: {e}")
        if 'backup_path' in locals() and os.path.exists(backup_path):
            os.replace(backup_path, file_path)

def format_file_size(size_bytes):
    """اندازه فایل را به یک رشته قابل خواندن برای انسان تبدیل می‌کند (مثلاً MB، GB)."""
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
    """تبدیل مدت زمان از ثانیه به فرمت دقیقه:ثانیه."""
    if duration_sec is None:
        return "نامشخص"
    try:
        minutes = int(duration_sec) // 60
        seconds = int(duration_sec) % 60
        return f"{minutes}:{seconds:02d}"
    except (ValueError, TypeError):
        return "نامشخص"

def check_file_exists(save_folder, title, ext):
    """چک می‌کند آیا فایل با نام مشابه در مسیر وجود دارد."""
    safe_title = "".join(c for c in title if c.isalnum() or c in " ._()")
    file_path = os.path.join(save_folder, f"{safe_title}.{ext}")
    return os.path.exists(file_path), file_path

def delete_partial_files(save_folder, title, ext):
    """حذف فایل‌های نیمه دانلود شده."""
    safe_title = "".join(c for c in title if c.isalnum() or c in " ._()")
    file_path = os.path.join(save_folder, f"{safe_title}.{ext}")
    part_path = file_path + '.part'
    if os.path.exists(file_path):
        try: os.remove(file_path)
        except OSError as e: logging.error(f"Error deleting file {file_path}: {e}")
    if os.path.exists(part_path):
        try: os.remove(part_path)
        except OSError as e: logging.error(f"Error deleting file {part_path}: {e}")


def download_thumbnail(url, save_path):
    """دانلود thumbnail از URL و ذخیره در مسیر."""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        return False
    except Exception as e:
        logging.error(f"Error downloading thumbnail: {e}")
        return False

# ---------------- Worker Classes (Threads) ----------------
class DownloaderThread(QThread):
    """رشته کارگر برای مدیریت فرآیند دانلود."""
    download_progress = pyqtSignal(dict)
    postprocess_progress = pyqtSignal(dict)
    download_finished = pyqtSignal(dict)
    download_error = pyqtSignal(str, str)
    download_cancelled = pyqtSignal(str)
    download_step = pyqtSignal(str, str)

    def __init__(self, id, url, ydl_opts, parent=None):
        super().__init__(parent)
        self.id = id
        self.url = url
        self.ydl_opts = ydl_opts
        self.is_cancelled = False

    def run(self):
        """متد اصلی برای اجرای دانلود."""
        def progress_hook(d):
            if self.is_cancelled:
                raise yt_dlp.utils.DownloadCancelled("Download cancelled by user")
            d['id'] = self.id
            d['phase'] = 'download'
            self.download_progress.emit(d)

        def postprocessor_hook(d):
            if self.is_cancelled:
                raise yt_dlp.utils.DownloadCancelled("Download cancelled by user")
            d['id'] = self.id
            d['phase'] = 'postprocess'
            self.postprocess_progress.emit(d)

        self.ydl_opts['progress_hooks'] = [progress_hook]
        self.ydl_opts['postprocessor_hooks'] = [postprocessor_hook]

        try:
            self.download_step.emit(self.id, "استخراج اطلاعات...")
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info_dict = ydl.extract_info(self.url, download=False)
                self.download_step.emit(self.id, "شروع دانلود...")
                ydl.download([self.url])
                info_dict['id'] = self.id
                self.download_finished.emit(info_dict)
        except yt_dlp.utils.DownloadCancelled:
            self.download_cancelled.emit(self.id)
        except yt_dlp.utils.DownloadError as e:
            error_str = str(e).lower()
            if "geo-restricted" in error_str:
                self.download_error.emit("ویدیو به دلیل محدودیت جغرافیایی در دسترس نیست. از پروکسی استفاده کنید.", self.id)
            elif "connectionreseterror" in error_str or "10054" in error_str:
                self.download_error.emit("اتصال توسط سرور قطع شد. لطفاً دوباره تلاش کنید.", self.id)
            else:
                self.download_error.emit(str(e), self.id)
        except Exception as e:
            self.download_error.emit(f"An unexpected error occurred: {e}", self.id)

class SettingsDialog(QDialog):
    """دیالوگ برای تنظیمات برنامه."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تنظیمات")
        self.setFixedSize(400, 300)
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
        
        self.clear_data_on_exit = QCheckBox("پاک کردن اطلاعات هنگام خروج")
        self.clear_data_on_exit.setChecked(self.parent_app.settings.get("clear_on_exit", False))
        main_layout.addRow(self.clear_data_on_exit)

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
    """دیالوگ برای انتخاب فیلدهای اطلاعاتی جهت ذخیره در فایل."""
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

class SingleDownloadTab(QWidget):
    """تب برای دانلود تکی ویدیو (اصلاح شده برای جلوگیری از هنگ کردن)."""
    info_fetched = pyqtSignal(dict)
    fetch_error = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.video_info = None
        self.thumbnail_pixmap = None
        self.downloader_thread = None

        layout = QVBoxLayout()

        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("آدرس ویدیو یوتیوب را وارد کنید...")
        self.fetch_btn = QPushButton("دریافت اطلاعات")
        self.fetch_btn.clicked.connect(self.fetch_video_info)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.fetch_btn)
        layout.addLayout(url_layout)

        self.info_label = QLabel("اطلاعات ویدیو:")
        self.info_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(self.info_label)

        self.title_label = QLabel()
        self.title_label.setFont(QFont("Arial", 11))
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        thumbnail_layout = QHBoxLayout()
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setFixedSize(200, 200)
        self.thumbnail_label.setStyleSheet(f"border: 1px solid {COLOR_GRID}; border-radius: 5px; background-color: {COLOR_BACKGROUND};")
        download_thumb_btn = QPushButton("دانلود تامنیل")
        download_thumb_btn.clicked.connect(self.download_single_thumbnail)
        thumbnail_layout.addWidget(self.thumbnail_label)
        thumbnail_layout.addWidget(download_thumb_btn)
        layout.addLayout(thumbnail_layout)

        options_layout = QHBoxLayout()
        quality_label = QLabel("کیفیت:")
        quality_label.setFont(QFont("Arial", 8))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(QUALITY_OPTIONS)
        options_layout.addWidget(quality_label)
        options_layout.addWidget(self.quality_combo)

        format_label = QLabel("فرمت:")
        format_label.setFont(QFont("Arial", 8))
        self.format_combo = QComboBox()
        self.format_combo.addItems(FORMAT_OPTIONS)
        self.format_combo.setCurrentText(self.parent_app.settings.get("format", "ویدیو و صدا"))
        options_layout.addWidget(format_label)
        options_layout.addWidget(self.format_combo)

        video_format_label = QLabel("فرمت خروجی ویدیو:")
        video_format_label.setFont(QFont("Arial", 10))
        self.video_format_combo = QComboBox()
        self.video_format_combo.addItems(VIDEO_FORMAT_OPTIONS)
        self.video_format_combo.setCurrentText(self.parent_app.settings.get("video_format", "mp4"))
        options_layout.addWidget(video_format_label)
        options_layout.addWidget(self.video_format_combo)
        
        subtitle_label = QLabel("زیرنویس:")
        subtitle_label.setFont(QFont("Arial", 8))
        self.subtitle_lang_combo = QComboBox()
        self.subtitle_lang_combo.addItems(SUBTITLE_LANGS)
        self.subtitle_lang_combo.setCurrentText(self.parent_app.settings.get("subtitle_lang", "هیچ"))
        options_layout.addWidget(subtitle_label)
        options_layout.addWidget(self.subtitle_lang_combo)
        
        layout.addLayout(options_layout)

        self.download_btn = QPushButton("دانلود ویدیو")
        self.download_btn.clicked.connect(self.start_single_download)
        self.download_btn.setEnabled(False)
        layout.addWidget(self.download_btn)

        self.cancel_btn = QPushButton("لغو دانلود")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_single_download)
        layout.addWidget(self.cancel_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)

        self.info_fetched.connect(self.on_info_fetched)
        self.fetch_error.connect(self.on_fetch_error)

    def fetch_video_info(self):
        url = self.url_input.text().strip()
        if not url:
            return
        
        self.fetch_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.title_label.setText("در حال دریافت اطلاعات...")
        self.thumbnail_label.clear()
        
        threading.Thread(target=self._thread_fetch_info, args=(url,), daemon=True).start()

    def _thread_fetch_info(self, url):
        try:
            ydl_opts = {'quiet': True}
            if self.parent_app.settings.get("proxy"):
                ydl_opts['proxy'] = self.parent_app.settings.get("proxy")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(url, download=False)

            thumbnail_data = None
            thumbnail_url = video_info.get('thumbnail')
            if thumbnail_url:
                session = requests.Session()
                retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
                session.mount('http://', HTTPAdapter(max_retries=retries))
                session.mount('https://', HTTPAdapter(max_retries=retries))
                response = session.get(thumbnail_url, timeout=10)
                if response.status_code == 200:
                    thumbnail_data = response.content
            
            self.info_fetched.emit({'video_info': video_info, 'thumbnail_data': thumbnail_data})
        except Exception as e:
            self.fetch_error.emit(str(e))
            
    def on_info_fetched(self, result):
        self.video_info = result['video_info']
        thumbnail_data = result['thumbnail_data']

        self.title_label.setText(f"عنوان: {self.video_info.get('title', 'نامشخص')}")
        
        if thumbnail_data:
            pixmap = QPixmap()
            pixmap.loadFromData(thumbnail_data)
            scaled_pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio)
            self.thumbnail_label.setPixmap(scaled_pixmap)
            self.thumbnail_pixmap = pixmap
        
        self.fetch_btn.setEnabled(True)
        self.download_btn.setEnabled(True)

    def on_fetch_error(self, error_msg):
        QMessageBox.warning(self, "خطا", f"خطا در دریافت اطلاعات: {error_msg}")
        self.title_label.setText("خطا در دریافت اطلاعات. لطفاً دوباره تلاش کنید.")
        self.fetch_btn.setEnabled(True)

    def download_single_thumbnail(self):
        if not self.thumbnail_pixmap:
            QMessageBox.warning(self, "خطا", "تامنیل موجود نیست.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره تامنیل", "", "تصاویر (*.jpg *.png)")
        if file_path:
            self.thumbnail_pixmap.save(file_path)

    def start_single_download(self):
        if not self.video_info:
            return

        save_folder = self.parent_app.settings.get("save_folder")
        if not save_folder or not os.path.isdir(save_folder):
            QMessageBox.warning(self, "خطا", "پوشه ذخیره نامعتبر است. لطفاً از تنظیمات یک پوشه انتخاب کنید.")
            return

        ydl_opts = {
            'outtmpl': os.path.join(save_folder, '%(title)s.%(ext)s'),
            'quiet': False,
            'retries': 10,
            'fragment_retries': 10,
        }
        if self.parent_app.settings.get("proxy"):
            ydl_opts['proxy'] = self.parent_app.settings.get("proxy")

        format_str = self.format_combo.currentText()
        if format_str == "فقط صدا":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]
        else:
            quality = self.quality_combo.currentText()
            video_format = self.video_format_combo.currentText()
            if quality == "بهترین":
                ydl_opts['format'] = 'bestvideo+bestaudio/best'
            elif quality == "بدترین":
                ydl_opts['format'] = 'worstvideo+worstaudio/worst'
            else:
                res = quality.replace("p", "")
                ydl_opts['format'] = f'bestvideo[height<={res}]+bestaudio/best[height<={res}]'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegVideoConvertor', 'preferedformat': video_format}]
        
        subtitle_lang = self.subtitle_lang_combo.currentText()
        if subtitle_lang != "هیچ":
            lang_code = subtitle_lang.split(' (')[1][:-1]
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] = [lang_code]
            ydl_opts['postprocessors'].append({'key': 'FFmpegSubtitlesConvertor', 'format': 'srt'})

        ffmpeg_path = get_ffmpeg_path()
        if ffmpeg_path:
            ydl_opts['ffmpeg_location'] = ffmpeg_path

        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)

        self.downloader_thread = DownloaderThread("single", self.video_info['webpage_url'], ydl_opts, self)
        self.downloader_thread.download_progress.connect(self.on_single_download_progress)
        self.downloader_thread.download_finished.connect(self.on_single_download_finished)
        self.downloader_thread.download_error.connect(self.on_single_download_error)
        self.downloader_thread.download_cancelled.connect(self.on_single_download_cancelled)
        self.downloader_thread.start()

    def cancel_single_download(self):
        if self.downloader_thread and self.downloader_thread.isRunning():
            self.downloader_thread.is_cancelled = True

    def on_single_download_progress(self, d):
        if d['status'] == 'downloading' and d.get('total_bytes'):
            percent = d.get('downloaded_bytes', 0) / d.get('total_bytes') * 100
            self.progress_bar.setValue(int(percent))

    def on_single_download_finished(self, info_dict):
        QMessageBox.information(self, "موفقیت", "دانلود با موفقیت انجام شد.")
        self.progress_bar.setValue(100)
        self.cancel_btn.setEnabled(False)
        self.download_btn.setEnabled(True)

    def on_single_download_error(self, error_msg, item_id):
        QMessageBox.warning(self, "خطا", f"خطا در دانلود: {error_msg}")
        self.progress_bar.setValue(0)
        self.cancel_btn.setEnabled(False)
        self.download_btn.setEnabled(True)

    def on_single_download_cancelled(self, item_id):
        QMessageBox.information(self, "لغو", "دانلود لغو شد.")
        self.progress_bar.setValue(0)
        self.cancel_btn.setEnabled(False)
        self.download_btn.setEnabled(True)

class App(QWidget):
    """پنجره اصلی برنامه."""
    thumbnail_loaded = pyqtSignal(str, QPixmap, str)
    video_info_loaded = pyqtSignal(int, dict)
    ui_update_signal = pyqtSignal(str, bool)

    def __init__(self):
        super().__init__()
        self.settings = {}
        self.download_queue = []
        self.active_downloads = []
        self.completed_downloads = []
        self.thread_pool = ThreadPoolExecutor(max_workers=os.cpu_count() or 4)
        self.yt_dlp_version = get_yt_dlp_version()
        self.ffmpeg_version = get_ffmpeg_version()
        self.id_to_row = {}
        self.downloading_all = False

        os.makedirs(THUMB_CACHE_DIR, exist_ok=True)

        self.load_settings()
        self.load_queue()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو در عنوان یا URL...")
        self.search_input.textChanged.connect(self.filter_table)

        self.setup_ui()
        self.apply_styles()
        self.apply_settings()
        self.restore_queue_to_table()
        self.check_dependencies()
        
        # self.thumbnail_loaded.connect(self._on_thumbnail_loaded)
        self.video_info_loaded.connect(self._add_to_table_from_thread)
        self.ui_update_signal.connect(self.update_ui_from_thread)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.viewport().installEventFilter(self)
        
        # Set window icon (assuming 'icon.png' is in the current directory)
        self.setWindowIcon(QIcon('icon.png'))

    def apply_styles(self):
        """Apply modern dark theme styles to the UI for a clean look."""
        font = QFont("Arial", 10)
        QApplication.setFont(font)
        
        style_sheet = f"""
            QWidget {{
                background-color: {COLOR_BACKGROUND};
                color: {COLOR_TEXT};
            }}
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: {COLOR_BACKGROUND};
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLOR_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {COLOR_SECONDARY};
            }}
            QLineEdit {{
                border: 1px solid {COLOR_GRID};
                border-radius: 8px;
                padding: 8px;
                background-color: {COLOR_SURFACE};
                color: {COLOR_TEXT};
            }}
            QTableWidget {{
                background-color: {COLOR_SURFACE};
                alternate-background-color: {COLOR_ALTERNATE};
                gridline-color: {COLOR_GRID};
                selection-background-color: {COLOR_ACCENT};
                color: {COLOR_TEXT};
                border-radius: 5px;
                
            }}
            QTableWidget::item {{
                padding: 2px;
            }}
            QHeaderView::section {{
                background-color: {COLOR_PRIMARY};
                color: {COLOR_BACKGROUND};
                padding: 8px;
                border: 1px solid {COLOR_BACKGROUND};
                font-weight: bold;
            }}
            QProgressBar {{
                background-color: {COLOR_GRID};
                border-radius: 8px;
                text-align: center;
                color: {COLOR_TEXT};
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {COLOR_SECONDARY};
                border-radius: 8px;
            }}
            QTabWidget::pane {{
                border: 1px solid {COLOR_GRID};
                background-color: {COLOR_SURFACE};
                border-radius: 5px;
            }}
            QTabBar::tab {{
                background-color: {COLOR_PRIMARY};
                color: {COLOR_BACKGROUND};
                padding: 10px 20px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background-color: {COLOR_SECONDARY};
            }}
            QLabel {{
                font-size: 12px;
                color: {COLOR_TEXT};
            }}
            QTextEdit {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_TEXT};
                border-radius: 5px;
            }}
            QComboBox {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_TEXT};
                border: 1px solid {COLOR_GRID};
                border-radius: 8px;
                padding: 4px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: {COLOR_GRID};
                border-left-style: solid;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
            QCheckBox {{
                color: {COLOR_TEXT};
            }}
            QMenu {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_TEXT};
                border: 1px solid {COLOR_GRID};
                border-radius: 5px;
            }}
            QMenu::item:selected {{
                background-color: {COLOR_SECONDARY};
            }}
        """
        self.setStyleSheet(style_sheet)

    def eventFilter(self, obj, event):
        if obj == self.table.viewport() and event.type() == QEvent.Type.Paint:
            self.load_visible_thumbnails()
        return super().eventFilter(obj, event)

    def load_visible_thumbnails(self):
        first_row = self.table.rowAt(self.table.viewport().rect().top())
        last_row = self.table.rowAt(self.table.viewport().rect().bottom())
        if first_row == -1: first_row = 0
        for row in range(first_row, min(self.table.rowCount(), last_row + 2)):
            if row < len(self.download_queue):
                item_id = self.download_queue[row]['id']
                thumbnail_widget = self.table.cellWidget(row, 0)
                if thumbnail_widget and hasattr(thumbnail_widget, 'text') and thumbnail_widget.text() == "در حال بارگذاری...":
                    thumbnail_url = self.download_queue[row].get("thumbnail_url")
                    if thumbnail_url:
                        self.thread_pool.submit(self._load_thumbnail, item_id, thumbnail_url)

    def setup_ui(self):
        """کامپوننت‌های اصلی UI را مقداردهی اولیه می‌کند."""
        self.setWindowTitle("دانلود کننده یوتیوب")
        self.setGeometry(100, 100, 1200, 700)

        main_layout = QVBoxLayout()
        self.create_menu_bar()
        main_layout.setMenuBar(self.menu_bar)

        self.tabs = QTabWidget()
        self.queue_tab = QWidget()
        self.single_tab = SingleDownloadTab(self)
        self.completed_tab = QWidget()
        self.logs_tab = QWidget()
        self.tabs.addTab(self.queue_tab, "صف دانلود")
        self.tabs.addTab(self.single_tab, "دانلود تکی")
        self.tabs.addTab(self.completed_tab, "دانلود شده‌ها")
        self.tabs.addTab(self.logs_tab, "لاگ عملیات")

        queue_layout = QVBoxLayout()
        queue_layout.addLayout(self._create_input_layout())
        queue_layout.addWidget(self.search_input)
        queue_layout.addLayout(self._create_table_layout())
        queue_layout.addLayout(self._create_controls_layout())
        self.queue_tab.setLayout(queue_layout)

        completed_layout = QVBoxLayout()
        self.completed_table = QTableWidget()
        self.completed_table.setColumnCount(8)
        self.completed_table.setHorizontalHeaderLabels(["عنوان", "لینک ویدیو", "حجم", "مدت زمان", "کیفیت", "وضعیت", "تاریخ آپلود", "مسیر ذخیره"])
        self.completed_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.completed_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.completed_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.completed_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.completed_table.customContextMenuRequested.connect(self.show_completed_context_menu)
        completed_layout.addWidget(self.completed_table)
        self.completed_tab.setLayout(completed_layout)
        
        logs_layout = QVBoxLayout()
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        logs_layout.addWidget(self.logs_text)
        self.logs_tab.setLayout(logs_layout)

        main_layout.addWidget(self.tabs)
        main_layout.addLayout(self._create_status_bar())
        self.setLayout(main_layout)

    def log_message(self, message):
        self.logs_text.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")

    def create_menu_bar(self):
        self.menu_bar = QMenuBar()
        file_menu = self.menu_bar.addMenu("فایل")
        import_action = QAction("وارد کردن از فایل", self)
        import_action.triggered.connect(self.import_from_file)
        file_menu.addAction(import_action)

        export_queue_menu = file_menu.addMenu("ذخیره اطلاعات صف")
        for ext in ["TXT", "JSON", "CSV"]:
            action = QAction(f"ذخیره به صورت {ext}", self)
            action.triggered.connect(lambda checked, e=ext.lower(): self.export_to_file(e))
            export_queue_menu.addAction(action)

        export_completed_action = QAction("ذخیره لیست دانلود شده‌ها", self)
        export_completed_action.triggered.connect(self.export_completed_list)
        file_menu.addAction(export_completed_action)
        
        file_menu.addSeparator()
        copy_all_urls_action = QAction("کپی کردن آدرس‌های صف", self)
        copy_all_urls_action.triggered.connect(self.copy_all_urls)
        file_menu.addAction(copy_all_urls_action)

        open_folder_action = QAction("باز کردن پوشه ذخیره", self)
        open_folder_action.triggered.connect(self.open_save_folder)
        file_menu.addAction(open_folder_action)

        clear_queue_action = QAction("پاک کردن صف", self)
        clear_queue_action.triggered.connect(self.clear_queue)
        file_menu.addAction(clear_queue_action)

        settings_menu = self.menu_bar.addMenu("تنظیمات")
        open_settings_action = QAction("باز کردن تنظیمات", self)
        open_settings_action.triggered.connect(self.show_settings_dialog)
        settings_menu.addAction(open_settings_action)

    def _create_input_layout(self):
        input_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("آدرس ویدیو یا پلی‌لیست یوتیوب را اینجا وارد کنید...")
        self.add_btn = QPushButton("اضافه کردن به صف")
        self.add_btn.clicked.connect(self.add_to_queue)
        input_layout.addWidget(self.url_input)
        input_layout.addWidget(self.add_btn)
        return input_layout

    def _create_table_layout(self):
        table_layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels(["عنوان", "لینک ویدیو", "حجم", "مدت زمان", "کیفیت", "فرمت", "زیرنویس", "وضعیت", "پیشرفت", "سرعت", "زمان باقی‌مانده", "لغو"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(11, QHeaderView.ResizeMode.Fixed)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        table_layout.addWidget(self.table)
        return table_layout

    def _create_controls_layout(self):
        controls_layout = QHBoxLayout()
        self.start_download_btn = QPushButton("شروع دانلودها")
        self.start_download_btn.clicked.connect(self.start_downloads)

        self.start_selected_btn = QPushButton("دانلود موارد انتخاب‌شده")
        self.start_selected_btn.clicked.connect(self.start_selected_downloads)

        self.cancel_download_btn = QPushButton("لغو همه")
        self.cancel_download_btn.setEnabled(False)
        self.cancel_download_btn.clicked.connect(self.cancel_all_downloads)
        
        self.remove_selected_btn = QPushButton("حذف موارد انتخاب‌شده")
        self.remove_selected_btn.clicked.connect(self.remove_selected_items)

        controls_layout.addWidget(self.start_download_btn)
        controls_layout.addWidget(self.start_selected_btn)
        controls_layout.addWidget(self.cancel_download_btn)
        controls_layout.addWidget(self.remove_selected_btn)
        return controls_layout

    def _create_status_bar(self):
        status_layout = QHBoxLayout()
        self.status_label = QLabel("آماده.")
        self.status_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        status_layout.addWidget(self.status_label)
        return status_layout

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return

        menu = QMenu()
        copy_urls_action = menu.addAction("کپی کردن آدرس(های) انتخاب شده")
        copy_titles_action = menu.addAction("کپی کردن عنوان(های) انتخاب شده")
        menu.addSeparator()
        
        export_selected_menu = menu.addMenu("ذخیره اطلاعات انتخاب شده")
        export_txt = export_selected_menu.addAction("به صورت TXT")
        export_json = export_selected_menu.addAction("به صورت JSON")
        export_csv = export_selected_menu.addAction("به صورت CSV")
        
        menu.addSeparator()
        download_thumb_action = menu.addAction("دانلود تامنیل")
        delete_action = menu.addAction("حذف ردیف")
        cancel_action = menu.addAction("لغو دانلود")
        start_single_action = menu.addAction("دانلود تکی")
        open_folder_action = menu.addAction("باز کردن پوشه دانلودها")
        
        action = menu.exec(self.table.mapToGlobal(pos))
        selected_rows = [index.row() for index in self.table.selectionModel().selectedRows()]

        if action == copy_urls_action: self.copy_selected_urls(selected_rows)
        elif action == copy_titles_action: self.copy_selected_titles(selected_rows)
        elif action == delete_action: self.remove_selected_items()
        elif action == cancel_action: 
            for row in selected_rows:
                self.cancel_single_download(row)
        elif action == start_single_action: 
            for row in selected_rows:
                self.start_single_download_from_menu(row)
        elif action == open_folder_action: self.open_save_folder()
        elif action == export_txt: self.export_selected_items("txt")
        elif action == export_json: self.export_selected_items("json")
        elif action == export_csv: self.export_selected_items("csv")
        elif action == download_thumb_action: self.download_selected_thumbnails(selected_rows)
            
    def show_completed_context_menu(self, pos):
        """منوی راست‌کلیک را برای جدول دانلود شده‌ها نمایش می‌دهد."""
        item = self.completed_table.itemAt(pos)
        if not item:
            return

        menu = QMenu()
        open_location_action = menu.addAction("باز کردن مسیر فایل")
        
        action = menu.exec(self.completed_table.mapToGlobal(pos))
        if action == open_location_action:
            self.open_file_location_from_completed(item.row())

    def open_file_location_from_completed(self, row):
        """پوشه حاوی فایل دانلود شده را باز می‌کند."""
        if not (0 <= row < len(self.completed_downloads)):
            return
            
        item = self.completed_downloads[row]
        path = item.get("download_path")
        
        if not (path and os.path.exists(path)):
            QMessageBox.warning(self, "فایل پیدا نشد", f"فایل در مسیر زیر وجود ندارد یا مسیر نامعتبر است:\n{path}")
            return
        
        try:
            if sys.platform == "win32":
                subprocess.run(['explorer', '/select,', os.path.normpath(path)], check=True)
            elif sys.platform == "darwin":
                subprocess.run(['open', '-R', path], check=True)
            else:
                subprocess.run(['xdg-open', os.path.dirname(path)], check=True)
        except Exception as e:
            self.log_message(f"خطا در باز کردن مسیر فایل: {e}")
            QMessageBox.critical(self, "خطا", f"خطا در باز کردن مسیر فایل: {e}")

    def copy_selected_titles(self, rows):
        if not rows:
            return
        titles = [self.download_queue[row]['title'] for row in rows if 0 <= row < len(self.download_queue)]
        if titles:
            QApplication.clipboard().setText("\n".join(titles))
            self.status_label.setText(f"{len(titles)} عنوان کپی شد.")

    def copy_selected_urls(self, rows):
        if not rows:
            return
        urls = [self.download_queue[row]['url'] for row in rows if 0 <= row < len(self.download_queue)]
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
                    QMessageBox.warning(self, "خطا", "URL تامنیل موجود نیست.")
                    continue
                
                safe_title = "".join(c for c in item['title'] if c.isalnum() or c in " ._()")
                file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره تامنیل", f"{safe_title}.jpg", "تصاویر (*.jpg *.png)")
                if file_path:
                    self.thread_pool.submit(download_thumbnail, url, file_path)

    def copy_all_urls(self):
        urls = "\n".join([item['url'] for item in self.download_queue])
        QApplication.clipboard().setText(urls)
        self.status_label.setText("تمامی آدرس‌ها در کلیپ‌بورد کپی شدند.")

    def open_save_folder(self):
        folder = self.settings.get("save_folder")
        if not os.path.exists(folder):
            QMessageBox.warning(self, "پوشه پیدا نشد", "پوشه ذخیره وجود ندارد. لطفاً در تنظیمات، یک پوشه معتبر انتخاب کنید.")
            return

        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            QMessageBox.critical(self, "خطا در باز کردن پوشه", f"خطا در باز کردن پوشه: {e}")

    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.settings["save_folder"] = dialog.folder_label.text()
            self.settings["format"] = dialog.format_combo.currentText()
            self.settings["video_format"] = dialog.video_format_combo.currentText()
            self.settings["concurrency"] = dialog.concurrency_spin.value()
            self.settings["proxy"] = dialog.proxy_input.text()
            self.settings["subtitle_lang"] = dialog.subtitle_lang_combo.currentText()
            self.settings["clear_on_exit"] = dialog.clear_data_on_exit.isChecked()
            self.save_settings()
            self.apply_settings()
            QMessageBox.information(self, "تنظیمات ذخیره شد", "تنظیمات با موفقیت ذخیره شدند.")

    def load_settings(self):
        self.settings = load_json_file(CONFIG_PATH, {
            "window_size": [1200, 700],
            "save_folder": os.path.join(os.path.expanduser("~"), "Downloads"),
            "format": "ویدیو و صدا",
            "video_format": "mp4",
            "concurrency": 3,
            "proxy": "",
            "subtitle_lang": "هیچ",
            "clear_on_exit": False
        })

    def apply_settings(self):
        window_size = self.settings.get("window_size", [1200, 700])
        self.resize(window_size[0], window_size[1])

    def save_settings(self):
        self.settings["window_size"] = [self.width(), self.height()]
        save_json_file(CONFIG_PATH, self.settings)

    def load_queue(self):
        self.download_queue = load_json_file(QUEUE_PATH, [])

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
            QMessageBox.warning(self, "فایل خالی", "فایل انتخاب شده حاوی هیچ آدرس معتبری نیست.")
    
    def _export_data_logic(self, data_list, file_type):
        """منطق اصلی برای ذخیره داده‌ها در فایل."""
        dialog = SaveDialog(self)
        if not dialog.exec():
            return

        fields = dialog.get_selected_fields()
        if not fields:
            QMessageBox.warning(self, "انتخابی صورت نگرفت", "لطفاً حداقل یک فیلد را برای ذخیره انتخاب کنید.")
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
                    writer.writerow(fields) # Write header
                    for item in data_list:
                        row_data = [item.get(self._get_field_key(field), 'نامشخص') for field in fields]
                        writer.writerow(row_data)
            QMessageBox.information(self, "ذخیره شد", f"اطلاعات با موفقیت در {os.path.basename(file_path)} ذخیره شد.")
        except IOError as e:
            QMessageBox.critical(self, "خطا", f"خطا در ذخیره فایل: {e}")

    def export_to_file(self, file_type):
        """صف دانلود فعلی را در یک فایل خروجی می‌گیرد."""
        if not self.download_queue:
            QMessageBox.warning(self, "صف خالی است", "هیچ موردی در صف دانلود وجود ندارد که ذخیره شود.")
            return
        self._export_data_logic(self.download_queue, file_type)

    def export_completed_list(self):
        """لیست دانلود شده‌ها را در یک فایل خروجی می‌گیرد."""
        if not self.completed_downloads:
            QMessageBox.warning(self, "لیست خالی است", "هیچ موردی در لیست دانلود شده‌ها وجود ندارد.")
            return

        file_type, _ = QInputDialog.getItem(self, "انتخاب فرمت", "فرمت فایل را انتخاب کنید:", ["TXT", "JSON", "CSV"], 0, False)
        if file_type:
            self._export_data_logic(self.completed_downloads, file_type.lower())

    def export_selected_items(self, file_type):
        """موارد انتخاب شده از صف را در یک فایل خروجی می‌گیرد."""
        selected_rows = [index.row() for index in self.table.selectionModel().selectedRows()]
        if not selected_rows:
            QMessageBox.warning(self, "هیچ انتخابی", "هیچ موردی برای ذخیره انتخاب نشده است.")
            return
        
        selected_items = [self.download_queue[row] for row in selected_rows]
        self._export_data_logic(selected_items, file_type)

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
        
    def add_to_queue(self):
        url = self.url_input.text().strip()
        if not url:
            return
        self.add_btn.setEnabled(False)
        self.status_label.setText("در حال دریافت اطلاعات ویدیو...")
        threading.Thread(target=self._fetch_and_add, args=(url,)).start()

    def _fetch_and_add(self, url):
        try:
            ydl_opts = {'quiet': True, 'extract_flat': True, 'force_generic_extractor': False}
            if self.settings.get("proxy"):
                ydl_opts['proxy'] = self.settings["proxy"]
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            if 'entries' in info:
                for entry in info.get('entries') or []:
                    if entry and entry.get('url'):
                        video_id_or_url = entry.get('url', '')
                        # Check if the URL is already a full URL or just an ID
                        if video_id_or_url.startswith('http'):
                            full_url = video_id_or_url
                        else:
                            full_url = f"https://www.youtube.com/watch?v={video_id_or_url}"
                        
                        entry['webpage_url'] = full_url
                        self.video_info_loaded.emit(-1, entry)
            elif info.get('webpage_url'):
                self.video_info_loaded.emit(-1, info)
        except Exception as e:
            self.ui_update_signal.emit(f"خطا در دریافت اطلاعات: {e}", True)
        finally:
            self.ui_update_signal.emit("آماده.", True)

    def update_ui_from_thread(self, status_text, enable_button):
        self.status_label.setText(status_text)
        self.add_btn.setEnabled(enable_button)

    def _add_to_table_from_thread(self, row, video_info):
        url = video_info.get("webpage_url", video_info.get("url", ""))
        if any(item['url'] == url for item in self.download_queue):
            return

        filesize = video_info.get('filesize_approx', video_info.get('filesize'))
        filesize_str = format_file_size(filesize)
        duration_str = format_duration(video_info.get('duration'))

        item_id = str(uuid.uuid4())
        
        item = {
            "id": item_id,
            "title": video_info.get("title", "نامشخص"),
            "url": url,
            "thumbnail_url": video_info.get("thumbnail", ""),
            "filesize_str": filesize_str,
            "duration_str": duration_str,
            "view_count": video_info.get("view_count", 0),
            "upload_date": video_info.get("upload_date", ""),
            "status": "در صف",
            "quality": self.settings.get("quality", "بهترین"),
            "format": self.settings.get("format", "ویدیو و صدا"),
            "video_format": self.settings.get("video_format", "mp4"),
            "subtitle_lang": self.settings.get("subtitle_lang", "هیچ"),
            "download_path": None
        }

        ext = 'mp3' if item["format"] == "فقط صدا" else item["video_format"]
        exists, path = check_file_exists(self.settings.get("save_folder"), item['title'], ext)
        if exists:
            item['status'] = "دانلود شده"
            item['download_path'] = path

        self.download_queue.append(item)
        self.id_to_row[item_id] = self.table.rowCount()
        self.save_queue()
        
        self.table.setRowCount(self.table.rowCount() + 1)
        self.update_table_row(self.table.rowCount() - 1, item)
        self.status_label.setText(f"'{item['title']}' به صف اضافه شد.")

    def _fetch_and_add_list(self, urls):
        for url in urls:
            try:
                ydl_opts = {'quiet': True, 'force_generic_extractor': False}
                if self.settings.get("proxy"):
                    ydl_opts['proxy'] = self.settings["proxy"]
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    self.video_info_loaded.emit(-1, info)
            except Exception:
                pass
        self.ui_update_signal.emit("وارد کردن آدرس‌ها به پایان رسید.", True)

    def restore_queue_to_table(self):
        self.table.setRowCount(len(self.download_queue))
        for row, item in enumerate(self.download_queue):
            item.setdefault('id', str(uuid.uuid4()))
            item.setdefault('subtitle_lang', self.settings.get("subtitle_lang", "هیچ"))
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
        self.table.setCellWidget(row, 4, quality_combo)
        
        format_combo = QComboBox()
        format_combo.addItems(FORMAT_OPTIONS)
        format_combo.setCurrentText(item.get("format", self.settings.get("format", "ویدیو و صدا")))
        self.table.setCellWidget(row, 5, format_combo)
        
        subtitle_combo = QComboBox()
        subtitle_combo.addItems(SUBTITLE_LANGS)
        subtitle_combo.setCurrentText(item.get("subtitle_lang", "هیچ"))
        self.table.setCellWidget(row, 6, subtitle_combo)
        
        self.table.setItem(row, 7, QTableWidgetItem(item.get("status")))

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
        self._start_next_downloads()

    def start_selected_downloads(self):
        if not self.check_dependencies(silent=False):
            return
        self.downloading_all = False
        selected_rows = [index.row() for index in self.table.selectionModel().selectedRows()]
        for row in selected_rows:
            item = self.download_queue[row]
            if item['status'] in ["در صف", "خطا", "لغو شده"]:
                self._start_single_download(row, item)

    def _start_next_downloads(self):
        concurrency = self.settings.get("concurrency", 3)
        while len(self.active_downloads) < concurrency:
            next_item_tuple = next(((i, item) for i, item in enumerate(self.download_queue) if item['status'] == "در صف"), None)
            if not next_item_tuple:
                break
            row, item = next_item_tuple
            self._start_single_download(row, item)
    
    def _start_single_download(self, row, item):
        if item['status'] == "دانلود شده":
            return
        
        item['quality'] = self.table.cellWidget(row, 4).currentText()
        item['format'] = self.table.cellWidget(row, 5).currentText()
        item['subtitle_lang'] = self.table.cellWidget(row, 6).currentText()
        self.save_queue()
        
        item['status'] = "در حال دانلود..."
        self.table.setItem(row, 7, QTableWidgetItem("در حال دانلود..."))

        safe_title = "".join(c for c in item['title'] if c.isalnum() or c in " ._()")
        ydl_opts = {
            'outtmpl': os.path.join(self.settings.get("save_folder"), f'{safe_title}.%(ext)s'),
            'retries': 10,
            'fragment_retries': 10,
            'quiet': False
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
                ydl_opts['format'] = 'bestvideo+bestaudio/best'
            elif quality_str == "بدترین":
                ydl_opts['format'] = 'worstvideo+worstaudio/worst'
            else:
                res = quality_str.replace("p", "")
                ydl_opts['format'] = f'bestvideo[height<={res}]+bestaudio/best[height<={res}]'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegVideoConvertor', 'preferedformat': video_format}]

        subtitle_lang = item['subtitle_lang']
        if subtitle_lang != "هیچ":
            lang_code = subtitle_lang.split(' (')[1][:-1]
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] = [lang_code]
            ydl_opts['postprocessors'].append({'key': 'FFmpegSubtitlesConvertor', 'format': 'srt'})

        ffmpeg_path = get_ffmpeg_path()
        if ffmpeg_path:
            ydl_opts['ffmpeg_location'] = ffmpeg_path

        self.table.setCellWidget(row, 8, QProgressBar())
        
        cancel_btn = QPushButton("لغو")
        cancel_btn.clicked.connect(lambda checked, r=row: self.cancel_single_download(r))
        self.table.setCellWidget(row, 11, cancel_btn)

        downloader = DownloaderThread(item['id'], item['url'], ydl_opts)
        downloader.download_progress.connect(self.on_download_progress)
        downloader.postprocess_progress.connect(self.on_postprocess_progress)
        downloader.download_finished.connect(self.on_download_finished)
        downloader.download_error.connect(self.on_download_error)
        downloader.download_cancelled.connect(self.on_download_cancelled)
        downloader.download_step.connect(self.on_download_step)
        self.active_downloads.append(downloader)
        downloader.start()

    def on_download_step(self, item_id, step_msg):
        row = self.id_to_row.get(item_id)
        if row is not None:
            self.log_message(f"[{self.download_queue[row]['title']}] {step_msg}")

    def on_download_progress(self, d):
        row = self.id_to_row.get(d['id'])
        if row is None or row >= self.table.rowCount(): return

        progress_bar = self.table.cellWidget(row, 8)
        if progress_bar and d['status'] == 'downloading':
            try:
                percent = float(d.get('_percent_str', '0%').strip().replace('%', ''))
                progress_bar.setValue(int(percent))
                speed_str = d.get('_speed_str', '').strip().replace(' ', '')  # Ensure speed is cleaned and displayed
                self.table.setItem(row, 9, QTableWidgetItem(speed_str))
                self.table.setItem(row, 10, QTableWidgetItem(d.get('_eta_str', '')))
            except (ValueError, AttributeError): pass

    def on_postprocess_progress(self, d):
        row = self.id_to_row.get(d['id'])
        if row is None or row >= self.table.rowCount(): return
        progress_bar = self.table.cellWidget(row, 8)
        if progress_bar:
            progress_bar.setValue(100 if d['status'] == 'finished' else 50)

    def on_download_finished(self, info_dict):
        item_id = info_dict['id']
        thread_index = self._find_thread_by_id(item_id)
        if thread_index != -1: self.active_downloads.pop(thread_index)
        
        row = self.id_to_row.get(item_id)
        if row is not None:
            item = self.download_queue.pop(row)
            item['status'] = "پایان یافت"
            item['download_path'] = info_dict.get('filepath') or info_dict.get('_filename')
            self.completed_downloads.append(item)
            self.table.removeRow(row)
            self._update_id_to_row_map()
            self.update_completed_table_row(self.completed_table.rowCount(), item)

        self.save_queue()
        self.check_all_finished()
        if self.downloading_all: self._start_next_downloads()

    def update_completed_table_row(self, row, item):
        self.completed_table.setRowCount(row + 1)
        self.completed_table.setItem(row, 0, QTableWidgetItem(item.get("title")))
        self.completed_table.setItem(row, 1, QTableWidgetItem(item.get("url")))
        self.completed_table.setItem(row, 2, QTableWidgetItem(item.get("filesize_str")))
        self.completed_table.setItem(row, 3, QTableWidgetItem(item.get("duration_str")))
        self.completed_table.setItem(row, 4, QTableWidgetItem(item.get("quality")))
        self.completed_table.setItem(row, 5, QTableWidgetItem(item.get("status")))
        date_str = item.get('upload_date', '')
        if date_str: self.completed_table.setItem(row, 6, QTableWidgetItem(f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:]}"))
        self.completed_table.setItem(row, 7, QTableWidgetItem(item.get("download_path")))
        
    def on_download_error(self, error_msg, item_id):
        self._handle_download_end(item_id, "خطا", error_msg)

    def on_download_cancelled(self, item_id):
        self._handle_download_end(item_id, "لغو شده", "دانلود توسط کاربر لغو شد.")
    
    def _handle_download_end(self, item_id, status, message):
        thread_index = self._find_thread_by_id(item_id)
        if thread_index != -1: self.active_downloads.pop(thread_index)

        row = self.id_to_row.get(item_id)
        if row is not None and row < self.table.rowCount():
            item = self.download_queue[row]
            self.table.setItem(row, 7, QTableWidgetItem(status))
            item['status'] = status
            cancel_btn = self.table.cellWidget(row, 11)
            if cancel_btn: cancel_btn.setEnabled(False)
            ext = 'mp3' if item.get('format') == "فقط صدا" else item.get('video_format', 'mp4')
            delete_partial_files(self.settings.get("save_folder"), item['title'], ext)
            self.log_message(f"'{item['title']}': {message}")
        
        self.save_queue()
        self.check_all_finished()
        if self.downloading_all: self._start_next_downloads()

    def _find_thread_by_id(self, item_id):
        return next((i for i, thread in enumerate(self.active_downloads) if thread.id == item_id), -1)
        
    def remove_selected_items(self):
        selected_rows = sorted([index.row() for index in self.table.selectionModel().selectedRows()], reverse=True)
        for row in selected_rows:
            self.remove_single_item(row)

    def remove_single_item(self, row):
        if not (0 <= row < self.table.rowCount()): return
        item = self.download_queue[row]
        self.cancel_single_download(row)
        
        del self.id_to_row[item['id']]
        del self.download_queue[row]
        self.table.removeRow(row)
        self._update_id_to_row_map()
        self.save_queue()

    def _update_id_to_row_map(self):
        self.id_to_row = {item['id']: i for i, item in enumerate(self.download_queue)}

    def cancel_single_download(self, row):
        if 0 <= row < len(self.download_queue):
            item = self.download_queue[row]
            thread_index = self._find_thread_by_id(item['id'])
            if thread_index != -1:
                self.active_downloads[thread_index].is_cancelled = True

    def start_single_download_from_menu(self, row):
        if 0 <= row < len(self.download_queue):
            self.downloading_all = False
            item = self.download_queue[row]
            if item['status'] in ["در صف", "خطا", "لغو شده"]:
                self._start_single_download(row, item)

    def cancel_all_downloads(self):
        for thread in list(self.active_downloads):
            thread.is_cancelled = True
        self.downloading_all = False

    def check_all_finished(self):
        if not self.active_downloads and not any(q['status'] == "در حال دانلود..." for q in self.download_queue):
            self.status_label.setText("عملیات دانلود به پایان رسید.")
            self.cancel_download_btn.setEnabled(False)
            self.start_download_btn.setEnabled(True)
            self.downloading_all = False

    def check_dependencies(self, silent=True):
        self.yt_dlp_version = get_yt_dlp_version()
        self.ffmpeg_version = get_ffmpeg_version()
        if not self.yt_dlp_version:
            if not silent: QMessageBox.critical(self, "وابستگی", "yt-dlp نصب نیست. لطفاً با 'pip install yt-dlp' نصب کنید.")
            return False
        if not self.ffmpeg_version:
            if not silent: QMessageBox.warning(self, "وابستگی", "ffmpeg نصب نیست. برای تبدیل فرمت‌ها لازم است.")
        return True
    
    def closeEvent(self, event):
        self.cancel_all_downloads()
        for thread in self.active_downloads:
            thread.wait() # Wait for cancellation to complete
        
        self.save_settings()
        self.thread_pool.shutdown(wait=True)
        
        if self.settings.get("clear_on_exit", False):
            if os.path.exists(CONFIG_PATH): os.remove(CONFIG_PATH)
            if os.path.exists(QUEUE_PATH): os.remove(QUEUE_PATH)

        event.accept()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec())