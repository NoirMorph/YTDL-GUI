# دانلودکننده یوتیوب

**دانلودکننده یوتیوب** یک برنامه گرافیکی ساده و قدرتمند برای دانلود ویدیوها و لیست‌های پخش از یوتیوب است. این برنامه از `yt-dlp` برای دانلود و `ffmpeg` برای تبدیل فرمت استفاده می‌کند و دارای رابط کاربری مدرن به زبان فارسی و انگلیسی است.

## ویژگی‌ها
- دانلود ویدیوهای تکی یا لیست‌های پخش کامل.
- پشتیبانی از کیفیت‌های مختلف (مثل 1080p، 720p، بهترین، بدترین).
- دانلود ویدیو با صدا، فقط صدا (MP3)، یا زیرنویس (مثل فارسی و انگلیسی).
- ادامه دانلودهای متوقف‌شده و مدیریت فایل‌های ناقص.
- تنظیمات قابل‌تغییر برای پوشه ذخیره، فرمت، پروکسی و تم (روشن، تیره، خودکار).
- خروجی گرفتن از صف دانلود به فرمت‌های TXT، JSON یا CSV.
- پشتیبانی از دو زبان انگلیسی و فارسی.

## پیش‌نیازها
### نرم‌افزارهای مورد نیاز
- **Python 3.8+**
- **PySide6**
- **requests**
- **yt-dlp**
- **ffmpeg**

### فایل‌های مورد نیاز
- پوشه `yt-dlp_bin/` حاوی فایل اجرایی `yt-dlp`.
- پوشه `ffmpeg_bin/` حاوی فایل اجرایی `ffmpeg`.
- فایل `icon.ico` در مسیر اصلی پروژه.

## نصب
### اجرای مستقیم
1. مخزن را کلون کنید:
   ```bash
   git clone https://github.com/NoirMorph/YTDL-GUI.git
   cd YTDL-GUI
   ```
2. وابستگی‌ها را نصب کنید:
   ```bash
   pip install PySide6 requests yt-dlp
   ```
3. فایل‌های `yt-dlp` و `ffmpeg` را در پوشه‌های مربوطه قرار دهید.
4. برنامه را اجرا کنید:
   ```bash
   python bugfixed.py
   ```

### ساخت فایل اجرایی
برای ویندوز (PowerShell):
```powershell
pyinstaller --name YouTubeDownloader `
     --onefile `
     --windowed `
     --noconsole `
     --icon ".\icon.ico" `
     --add-data "yt-dlp_bin;yt-dlp_bin" `
     --add-data "ffmpeg_bin;ffmpeg_bin" `
     --add-data "icon.ico;." `
     --noconfirm `
     --upx-dir "C:\tools\upx" `
     --upx-exclude vcruntime140.dll `
     --upx-exclude ucrtbase.dll `
     --upx-exclude python312.dll `
     --hidden-import yt_dlp `
     --hidden-import PySide6.QtGui `
     --hidden-import PySide6.QtWidgets `
     --hidden-import PySide6.QtCore `
     --hidden-import requests `
     --hidden-import urllib3 `
     --exclude-module numpy `
     --exclude-module scipy `
     --exclude-module matplotlib `
     --exclude-module pandas `
     --clean `
    .\YTDL-GUI.py
```

### ایجاد نصب‌کننده ویندوز
1. اسکریپت `YouTubeDownloader.iss` را در Inno Setup Compiler باز کنید.
2. اسکریپت را کامپایل کنید تا `YouTubeDownloader_Setup.exe` ایجاد شود.
3. نصب‌کننده را اجرا کنید.

## استفاده
1. برنامه را اجرا کنید.
2. آدرس ویدیوی یوتیوب یا لیست پخش را وارد کنید و روی **"اضافه کردن به صف"** کلیک کنید.
3. در تنظیمات، گزینه‌های دلخواه (پوشه ذخیره، فرمت، کیفیت، زیرنویس) را انتخاب کنید.
4. روی **"شروع دانلود"** کلیک کنید و پیشرفت را در جدول مشاهده کنید.
5. برای لیست‌های پخش بزرگ، از `?playlist_items=1-50` در آدرس استفاده کنید.

## نکات مهم
- برای لیست‌های پخش بزرگ، تعداد آیتم‌ها را محدود کنید تا از هنگ کردن رابط کاربری جلوگیری شود.
- برای کاهش زمان تبدیل، فرمت `webm` را انتخاب کنید.
- فایل‌های تنظیمات در `%APPDATA%\YouTubeDownloader` ذخیره می‌شوند.

## عیب‌یابی
- **خطای پیدا نشدن yt-dlp یا ffmpeg**: مطمئن شوید فایل‌های اجرایی در پوشه‌های درست قرار دارند.
- **هنگ کردن برای لیست‌های پخش بزرگ**: تعداد آیتم‌ها را محدود کنید.
- **کند بودن تبدیل فرمت**: از فرمت `webm` استفاده کنید.

## تماس
برای پشتیبانی، با [NoirMorph](https://github.com/NoirMorph) تماس بگیرید یا یک Issue در GitHub باز کنید.


---


# YouTubeDownloader

**YouTubeDownloader** is a user-friendly GUI application built with Python and PySide6 for downloading videos and playlists from YouTube. It leverages `yt-dlp` for downloading and `ffmpeg` for format conversion, providing a robust solution for managing YouTube downloads with a modern interface.

## Features
- Download single videos or entire playlists from YouTube.
- Support for various quality options (e.g., 1080p, 720p, best, worst).
- Download video with audio, audio-only (MP3), or subtitles in multiple languages (e.g., English, Persian).
- Resume interrupted downloads and manage partial files.
- Customizable settings for download folder, format, proxy, and theme (Light/Dark/Auto).
- Export download queue to TXT, JSON, or CSV formats.
- Multilingual support (English and Persian).
- Cross-platform compatibility (Windows, macOS, Linux).

## Prerequisites
To run or build the YouTubeDownloader application, ensure the following are installed:

### Software Requirements
- **Python 3.8+**: Required to run the source code.
- **PySide6**: For the graphical user interface.
- **requests**: For handling HTTP requests.
- **yt-dlp**: For downloading videos and playlists.
- **ffmpeg**: For video/audio format conversion.

### File Dependencies
- **`yt-dlp_bin/`**: Must contain the `yt-dlp` executable (`yt-dlp.exe` for Windows, `yt-dlp` for Linux/macOS).
- **`ffmpeg_bin/`**: Must contain the `ffmpeg` executable (`ffmpeg.exe` for Windows, `ffmpeg` for Linux/macOS).
- **`icon.ico`**: The application icon file, located in the project root.

### Optional
- **UPX**: For compressing the executable when building with PyInstaller (optional, but recommended for smaller file sizes).
- **Inno Setup**: For creating a Windows installer (optional).

## Installation

### Running from Source
1. Clone the repository:
   ```bash
   git clone https://github.com/NoirMorph/YTDL-GUI.git
   cd YTDL-GUI
   ```

2. Install Python dependencies:
   ```bash
   pip install PySide6 requests yt-dlp
   ```

3. Download `yt-dlp` and `ffmpeg`:
   - Place the `yt-dlp` executable in the `yt-dlp_bin/` folder.
   - Place the `ffmpeg` executable in the `ffmpeg_bin/` folder.
   - Alternatively, the application will attempt to download these tools automatically if not found.

4. Run the application:
   ```bash
   python bugfixed.py
   ```

### Building the Executable
To create a standalone executable, use PyInstaller. The following command is for Windows (PowerShell):

```powershell
pyinstaller --name YouTubeDownloader `
    --onefile `
    --windowed `
    --noconsole `
    --icon ".\icon.ico" `
    --add-data "yt-dlp_bin;yt-dlp_bin" `
    --add-data "ffmpeg_bin;ffmpeg_bin" `
    --add-data "icon.ico;." `
    --noconfirm `
    --upx-dir "C:\tools\upx" `
    --hidden-import yt_dlp `
    --hidden-import PySide6.QtGui `
    --hidden-import PySide6.QtWidgets `
    --hidden-import PySide6.QtCore `
    .\YTDL-GUI.py
```

- The executable will be created in the `dist/` folder as `YouTubeDownloader.exe`.
- For Linux/macOS, replace the `;` separator in `--add-data` with `:` and use the appropriate `yt-dlp` and `ffmpeg` binaries.

### Creating a Windows Installer
To create a Windows installer, use the provided Inno Setup script (`YouTubeDownloader.iss`):

1. Ensure Inno Setup is installed.
2. Open `YouTubeDownloader.iss` in Inno Setup Compiler.
3. Compile the script to generate `YouTubeDownloader_Setup.exe` in the `Output/` folder.
4. Run the installer to set up the application on a Windows system.

## Usage
1. **Launch the Application**:
   - Run `YouTubeDownloader.exe` (if built) or `python bugfixed.py` (if running from source).

2. **Add Videos or Playlists**:
   - Enter a YouTube video or playlist URL in the input field.
   - Click **"اضافه کردن به صف"** (Add to Queue) to fetch video details.
   - For large playlists, consider limiting the number of items using `?playlist_items=1-50` in the URL to avoid UI freezing.

3. **Customize Download Settings**:
   - Go to **Settings** (تنظیمات) to configure:
     - Save folder (default: `~/Downloads`).
     - Download format (Video + Audio or Audio Only).
     - Video quality (e.g., 1080p, 720p).
     - Subtitle language (e.g., Persian, English).
     - Proxy settings (if needed).
     - Theme (Light, Dark, or Auto).

4. **Start Downloads**:
   - Select items in the queue and click **"شروع دانلود"** (Start Download).
   - Monitor progress in the table (progress bar, downloaded size, speed, ETA).
   - Pause, resume, or cancel downloads as needed.

5. **Export Queue**:
   - Export the download queue to TXT, JSON, or CSV via the **File** menu.

6. **View Logs**:
   - Check the log window at the bottom for detailed status updates.

## Important Notes
- **Large Playlists**: To avoid UI freezing, limit playlist items using `?playlist_items=1-100` in the URL or increase the batch size in the code (already set to 100 with a 0.5-second delay).
- **Format Conversion**: The application prioritizes MP4 downloads to minimize conversion time. If conversion is slow, switch to `webm` format in settings to skip conversion.
- **Dependencies**: Ensure `yt-dlp` and `ffmpeg` are in the correct folders (`yt-dlp_bin/` and `ffmpeg_bin/`). The application will attempt to download them if missing, but manual placement is recommended for reliability.
- **Windows-Specific**: The provided PyInstaller and Inno Setup scripts are optimized for Windows. For Linux/macOS, adjust the `--add-data` separators and use appropriate binaries.
- **Configuration Storage**: Settings and cache are stored in `%APPDATA%\YouTubeDownloader` (Windows) or equivalent user data directories on other platforms.

## Troubleshooting
- **"yt-dlp or ffmpeg not found"**: Ensure the `yt-dlp_bin/` and `ffmpeg_bin/` folders contain the correct executables. Check the log for details.
- **UI Freezing with Large Playlists**: Use the `?playlist_items` URL parameter to limit items or increase the batch processing delay in the code.
- **Slow Conversion**: Switch to `webm` format in settings to avoid FFmpeg conversion.
- **Executable Issues**: If the executable fails to run, ensure all dependencies (e.g., Microsoft Visual C++ Redistributable) are installed. Check the PyInstaller log in the `build/` folder for errors.

## Contributing
Contributions are welcome! To contribute:
1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Make your changes and commit (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a Pull Request.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.

## Contact
For questions or support, contact [NoirMorph](https://github.com/NoirMorph) or open an issue on GitHub.
