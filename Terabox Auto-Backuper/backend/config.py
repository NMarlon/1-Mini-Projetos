"""Configurações globais do aplicativo."""

import os
from pathlib import Path

# Diretório raiz do projeto
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
FRONTEND_DIR = PROJECT_DIR / "frontend"

# Servidor
HOST = "127.0.0.1"
PORT = 8765

# Banco de dados
DB_PATH = DATA_DIR / "app.db"

# Terabox
BASE_URL_TB = "https://www.terabox.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
APP_ID = "250528"
CHANNEL = "dubox"
CLIENT_TYPE = "5"

# Sync
DEFAULT_SYNC_INTERVAL_MINUTES = 30
DEFAULT_MAX_CONCURRENT = 3
DEFAULT_RATE_LIMIT_MS = 400
DEFAULT_DEBOUNCE_SECONDS = 2
MAX_RETRIES = 3

# Upload em blocos (lotes). O usuário pode desligar em Configurações.
CHUNK_SIZE_BYTES = 100 * 1024 * 1024  # 100MB
LARGE_FILE_THRESHOLD = CHUNK_SIZE_BYTES

# Timeouts e proteção contra upload travado.
UPLOAD_CONNECT_TIMEOUT_SECONDS = 30
UPLOAD_STALL_SECONDS = 120          # curl aborta se ficar abaixo da velocidade mínima
UPLOAD_MIN_SPEED_BPS = 1024         # 1 KB/s
UPLOAD_MAX_TIME_SECONDS = 4 * 3600  # teto absoluto por bloco
UPLOAD_MIN_BYTES_PER_SECOND = 128 * 1024  # usado para calcular --max-time
UPLOAD_NO_PROGRESS_SECONDS = 300    # watchdog do motor

# jsToken
JSTOKEN_TTL_SECONDS = 300  # 5 minutos

# Configuração remota de mapeamentos
DEFAULT_REMOTE_CONFIG_PATH = (
    "/config-terabox-auto-backup/terabox-auto-backup.json"
)
REMOTE_CONFIG_SHORTCUT_PATH = "/_terabox_autobackup_config.json"

# Temp
TEMP_DIR = PROJECT_DIR / "temp"

# Garantir que diretórios existam
DATA_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)