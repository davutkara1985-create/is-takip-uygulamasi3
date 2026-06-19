"""Application-wide constants for TÜRKAK İş Yönetim Sistemi."""
from __future__ import annotations

APP_TITLE = "TÜRKAK İş Yönetim Sistemi"
APP_ICON = "🏛️"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "Turkak2026!"
DEFAULT_ADMIN_EMAIL = "admin@turkak.org.tr"

ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
ROLE_STAFF = "staff"
ROLES = [ROLE_ADMIN, ROLE_MANAGER, ROLE_STAFF]
ROLE_LABELS = {
    ROLE_ADMIN: "Admin",
    ROLE_MANAGER: "Yönetici",
    ROLE_STAFF: "Personel",
}

IDEA_STATUSES = ["fikir", "araştırılıyor", "hazır"]
TIMELINE_TYPES = ["iş", "sosyal medya", "toplantı", "kütüphane", "bildirim", "diğer"]
NOTIFICATION_CHANNELS = ["app", "email", "app+email"]
FONT_SIZE_OPTIONS = {
    "Normal": "16px",
    "Büyük": "18px",
    "Çok büyük": "20px",
}
THEME_OPTIONS = ["Açık", "Koyu"]
DATE_FORMAT = "%d.%m.%Y"
