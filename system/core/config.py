# SYSTEM Hub Configuration
import os

APP_NAME = "SYSTEM v1.0"
COMPANY_NAME = "Antigravity Inc."

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODULES_DIR = os.path.join(BASE_DIR, "modules")

# THEME: "Neon Cyber"
# Deep Dark background with Neon Cyan accents
THEME = {
    "colors": {
        "bg_main": "#0f0f13",       # Ultra Dark Blue/Gray
        "bg_sidebar": "#16161c",    # Slightly Lighter
        "bg_card": "#1f1f26",       # Card Background
        "bg_card_hover": "#2a2a33", # Card Hover
        "surface_variant": "#25252e", # Slightly lighter than card for variants
        
        "text_primary": "#ffffff",
        "text_secondary": "#a0a0a0",
        
        "accent": "#00d9ff",        # Neon Cyan
        "accent_hover": "#00b8d4",
        "accent_text": "#000000",
        
        "danger": "#ff1744",        # Neon Red
        "success": "#00e676",       # Neon Green
        "success_hover": "#00c853", # Darker Green
        "border": "#2c2c36"
    },
    "fonts": {
        "header": ("Roboto", 24, "bold"),
        "subheader": ("Roboto", 18, "bold"),
        "body": ("Roboto", 14),
        "small": ("Roboto", 11)
    }
}
