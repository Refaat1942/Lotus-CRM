import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "lotus-crm-change-me-in-production")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://lotus:lotus@localhost:5432/lotus_crm",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "ar")
    APP_PORT = int(os.getenv("APP_PORT", "16350"))
    BACKUP_DIR = os.getenv("BACKUP_DIR", "/backups")
    BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "app/static/uploads")
    STATIC_VERSION = os.getenv("STATIC_VERSION", "20260705a")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
