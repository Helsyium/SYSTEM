#!/bin/bash
DIR=$(cd "$(dirname "$0")"; pwd)
PROJECT_ROOT="$DIR"

echo "==================================================="
echo "  SYSTEM HUB - Antigravity Inc."
echo "  Platform: macOS"
echo "==================================================="

export PYTHONPATH="$PROJECT_ROOT"

# Sanal Ortam (venv) Kontrolü
VENV_DIR="$PROJECT_ROOT/venv"

# 1. En uygun Python Sürümünü Bul (Homebrew öncelikli)
# macOS 15+ sorunları için güncel Python (3.11+) şart.
PYTHON_EXEC=""

CANDIDATES=(
    "/opt/homebrew/bin/python3.13"
    "/opt/homebrew/bin/python3.12"
    "/opt/homebrew/bin/python3.11"
    "/opt/homebrew/bin/python3"
    "/usr/local/bin/python3.13"
    "/usr/local/bin/python3.12"
    "/usr/local/bin/python3"
)

echo "[BILGI] Uygun Python sürümü aranıyor..."

for cmd in "${CANDIDATES[@]}"; do
    if [ -x "$cmd" ]; then
        PYTHON_EXEC="$cmd"
        break
    fi
done

# Eğer bulamadıysa sistemdekine bak
if [ -z "$PYTHON_EXEC" ]; then
    if command -v python3 &>/dev/null; then
        PYTHON_EXEC=$(command -v python3)
    fi
fi

if [ -z "$PYTHON_EXEC" ]; then
    echo "[HATA] Python 3 bulunamadı! Lütfen Homebrew ile kurun: brew install python"
    read -p "Kapatmak için Enter..."
    exit 1
fi

echo "[BILGI] Seçilen Python: $PYTHON_EXEC"

# 2. venv Oluştur (Eğer yoksa)
if [ ! -d "$VENV_DIR" ]; then
    echo "[BILGI] İlk kurulum yapılıyor (Sanal ortam oluşturuluyor)..."
    "$PYTHON_EXEC" -m venv "$VENV_DIR"
    
    if [ $? -ne 0 ]; then
         echo "[HATA] Sanal ortam oluşturulamadı. 'python3-venv' kurulu mu?"
         read -p "Kapatmak için Enter..."
         exit 1
    fi
fi

# 3. Bağımlılıkları Yükle
echo "[BILGI] Bağımlılıklar denetleniyor..."
"$VENV_DIR/bin/pip" install -r "$PROJECT_ROOT/requirements.txt"

if [ $? -ne 0 ]; then
    echo "[UYARI] Bazı paketler yüklenemedi. Devam ediliyor..."
fi

# 4. Başlat
echo "[BILGI] SYSTEM arayüzü başlatılıyor..."
"$VENV_DIR/bin/python3" "$PROJECT_ROOT/system/main.py"

if [ $? -ne 0 ]; then
    echo ""
    echo "[HATA] Uygulama beklenmedik şekilde kapandı."
    # Hata analizi için ipucu
    echo "İpucu: 'Abort trap' hatası alıyorsanız Python sürümünüz macOS ile uyumsuzdur."
    echo "Çözüm: brew install python komutuyla güncel Python kurun."
    read -p "Pencereyi kapatmak için Enter..."
fi
