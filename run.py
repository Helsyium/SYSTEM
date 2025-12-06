import sys
import os

# PyInstaller ile çalışırken path sorunlarını önlemek için
# Eğer bundle içindeysek, sys._MEIPASS'ı path'e ekle (gerçi PyInstaller bunu yapar)
# Ama asıl önemli olan, bu script proje kökünde çalışacağı için folder_locker'ı görebilecek.

try:
    from folder_locker.main import main
except ImportError:
    # Eğer path sorunu varsa manuel ekle
    sys.path.append(os.path.join(os.path.dirname(__file__)))
    from folder_locker.main import main

if __name__ == '__main__':
    main()
