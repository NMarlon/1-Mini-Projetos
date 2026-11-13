"""Modelos Pydantic e definições de tabelas SQLite."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ── Mapeamentos ──

class MappingCreate(BaseModel):
    name: str
    local_path: str
    remote_path: str
    include_subfolders: bool = True
    encrypt: bool = False
    enabled: bool = True
    is_file: Optional[bool] = None

class MappingUpdate(BaseModel):
    name: Optional[str] = None
    local_path: Optional[str] = None
    remote_path: Optional[str] = None
    include_subfolders: Optional[bool] = None
    encrypt: Optional[bool] = None
    enabled: Optional[bool] = None
    is_file: Optional[bool] = None

class Mapping(BaseModel):
    id: int
    name: str
    local_path: str
    remote_path: str
    include_subfolders: bool
    encrypt: bool
    enabled: bool
    created_at: str
    updated_at: str
    is_file: bool = False
    uid: str = ""

class MappingBulkEnabled(BaseModel):
    ids: List[int]
    enabled: bool

# ── Arquivos ──

class FileRecord(BaseModel):
    id: int
    mapping_id: int
    local_rel_path: str
    remote_path: str
    size: int
    md5: Optional[str] = None
    remote_md5: Optional[str] = None
    mtime_ns: Optional[int] = None
    encrypted: bool = False
    status: str = "pending"  # pending, uploaded, failed
    last_synced_at: Optional[str] = None
    error: Optional[str] = None

# ── Sync Runs ──

class SyncRun(BaseModel):
    id: int
    started_at: str
    finished_at: Optional[str] = None
    status: str = "running"  # running, completed, failed, cancelled
    files_total: int = 0
    files_uploaded: int = 0
    files_failed: int = 0
    files_skipped: int = 0
    error: Optional[str] = None

class SyncStatus(BaseModel):
    running: bool = False
    run_id: Optional[int] = None
    phase: str = "idle"
    started_at: Optional[str] = None
    files_total: int = 0
    files_uploaded: int = 0
    files_failed: int = 0
    files_skipped: int = 0
    files_processed: int = 0
    current_file: Optional[str] = None
    current_mapping: Optional[str] = None
    error: Optional[str] = None
    errors: List[dict] = Field(default_factory=list)


class SyncRequest(BaseModel):
    mapping_ids: Optional[List[int]] = None


class CsvImportRequest(BaseModel):
    csv: str
    include_subfolders: bool = True
    encrypt: bool = False
    enabled: bool = True
    dry_run: bool = False

# ── Configurações ──

class Settings(BaseModel):
    sync_interval_minutes: int = 30
    auto_sync: bool = True
    notifications: bool = True
    max_concurrent_uploads: int = 3
    autostart: bool = False
    browser_preference: str = "auto"  # auto, chrome, edge, firefox
    encryption_key: Optional[str] = None
    restore_confirm_overwrite: bool = True
    machine_name: str = ""
    remote_config_enabled: bool = True
    remote_config_path: str = "/config-terabox-auto-backup/terabox-auto-backup.json"
    remote_config_auto_save: bool = True

class SettingsUpdate(BaseModel):
    sync_interval_minutes: Optional[int] = None
    auto_sync: Optional[bool] = None
    notifications: Optional[bool] = None
    max_concurrent_uploads: Optional[int] = None
    autostart: Optional[bool] = None
    browser_preference: Optional[str] = None
    encryption_key: Optional[str] = None
    restore_confirm_overwrite: Optional[bool] = None
    machine_name: Optional[str] = None
    remote_config_enabled: Optional[bool] = None
    remote_config_path: Optional[str] = None
    remote_config_auto_save: Optional[bool] = None

# ── Auth ──

class AuthStatus(BaseModel):
    authenticated: bool = False
    browser: Optional[str] = None
    cookies_found: int = 0
    jstoken_expires_in: Optional[int] = None
    error: Optional[str] = None
    connecting: bool = False

class AuthConnect(BaseModel):
    browser: str = "auto"
    profile: Optional[str] = None

class AuthConnectManual(BaseModel):
    cookies: str

class BrowserProfile(BaseModel):
    name: str
    path: str
    is_default: bool = False
    has_terabox: Optional[bool] = None  # None = desconhecido (arquivo bloqueado)

# ── Restaurar ──

class RestoreFile(BaseModel):
    local_rel_path: str
    remote_path: str
    size: int
    md5: Optional[str] = None
    remote_md5: Optional[str] = None
    mapping_name: Optional[str] = None
    synced_at: Optional[str] = None
    encrypted: bool = False

class RestorePlanRequest(BaseModel):
    files: List[str]

class RestoreRequest(BaseModel):
    files: List[str]
    allow_overwrite: bool = False

class RestoreStatus(BaseModel):
    running: bool = False
    job_id: Optional[str] = None
    phase: str = "idle"
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    elapsed_seconds: float = 0.0
    files_total: int = 0
    files_done: int = 0
    files_created: int = 0
    files_replaced: int = 0
    files_failed: int = 0
    files_invalid: int = 0
    current_index: int = 0
    current_file: Optional[str] = None
    current_mapping: Optional[str] = None
    current_remote_path: Optional[str] = None
    cancel_requested: bool = False
    error: Optional[str] = None
    errors: List[dict] = Field(default_factory=list)
    errors_truncated: bool = False
    summary: Optional[dict] = None

# ── Configuração remota ──

class RemoteConfigSaveRequest(BaseModel):
    force: bool = False

class RemoteConfigImportItem(BaseModel):
    uid: str
    local_path: str

class RemoteConfigImportRequest(BaseModel):
    config_hash: str = ""
    mappings: List[RemoteConfigImportItem] = Field(default_factory=list)
    adopt_path: bool = True

# ── Health ──

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.3.5"