import asyncio
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import UserRole
from app.database import get_db
from app.dependencies import require_roles
from app.models.backup_notification_recipient import BackupNotificationRecipient

router = APIRouter(prefix="/api/settings/backup", tags=["Backup"])

_super_admin_only = require_roles(UserRole.SUPER_ADMIN)

# Backup directory — mounted as a volume in Docker
BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "/app/backups"))


# ── Schemas ─────────────────────────────────────────────────────────────

class BackupFileOut(BaseModel):
    filename: str
    size_bytes: int
    size_human: str
    created_at: str
    gdrive_synced: bool | None = None

class BackupStatusOut(BaseModel):
    last_backup_time: str | None = None
    last_backup_file: str | None = None
    last_backup_size: str | None = None
    last_backup_status: str | None = None
    last_sync_time: str | None = None
    last_synced_file: str | None = None
    last_sync_status: str | None = None
    gdrive_backup_count: int | None = None
    schedule: str = "Daily at 2:00 AM"
    local_retention_days: int = 7
    gdrive_retention_days: int = 30

class BackupTriggerOut(BaseModel):
    message: str
    status: str

class RecipientCreate(BaseModel):
    email: EmailStr
    label: str | None = None

class RecipientOut(BaseModel):
    id: int
    email: str
    label: str | None
    is_active: bool
    model_config = {"from_attributes": True}


# ── Helpers ──────────────────────────────────────────────────────────────

def _human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

def _read_json_file(path: Path) -> dict | None:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return None

def _parse_backup_time(filename: str) -> str | None:
    """Extract datetime from filename like ssmspl_db_prod_20260402_020000.sql.gz"""
    match = re.search(r'(\d{8}_\d{6})', filename)
    if match:
        try:
            dt = datetime.strptime(match.group(1), '%Y%m%d_%H%M%S')
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            pass
    return None


# ── Status endpoint ──────────────────────────────────────────────────────

@router.get("/status", response_model=BackupStatusOut, summary="Get backup status")
async def get_backup_status(current_user=Depends(_super_admin_only)):
    result = BackupStatusOut()

    # Read last backup status
    backup_status = _read_json_file(BACKUP_DIR / ".last_backup.json")
    if backup_status:
        result.last_backup_time = backup_status.get("time")
        result.last_backup_file = backup_status.get("file")
        result.last_backup_size = backup_status.get("size_human")
        result.last_backup_status = backup_status.get("status")

    # Read sync status
    sync_status = _read_json_file(BACKUP_DIR / ".sync_status.json")
    if sync_status:
        result.last_sync_time = sync_status.get("time")
        result.last_synced_file = sync_status.get("file")
        result.last_sync_status = sync_status.get("status")
        result.gdrive_backup_count = sync_status.get("gdrive_count")

    # If no status files, try to infer from directory listing
    if not backup_status:
        try:
            backups = sorted(BACKUP_DIR.glob("*.sql.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
            if backups:
                latest = backups[0]
                stat = latest.stat()
                result.last_backup_file = latest.name
                result.last_backup_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                result.last_backup_size = _human_size(stat.st_size)
                result.last_backup_status = "success"
        except OSError:
            pass

    return result


# ── History endpoint ─────────────────────────────────────────────────────

@router.get("/history", response_model=list[BackupFileOut], summary="List recent backups")
async def get_backup_history(current_user=Depends(_super_admin_only)):
    backups = []
    sync_status = _read_json_file(BACKUP_DIR / ".sync_status.json")
    synced_files: set[str] = set()

    # Build set of synced files from sync log
    sync_log = BACKUP_DIR / ".sync_log.json"
    sync_log_data = _read_json_file(sync_log)
    if sync_log_data and isinstance(sync_log_data, list):
        synced_files = {entry.get("file", "") for entry in sync_log_data}
    # Also add the most recently synced file
    if sync_status:
        synced_files.add(sync_status.get("file", ""))

    try:
        files = sorted(BACKUP_DIR.glob("*.sql.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
        for f in files[:30]:  # Last 30 backups max
            stat = f.stat()
            backups.append(BackupFileOut(
                filename=f.name,
                size_bytes=stat.st_size,
                size_human=_human_size(stat.st_size),
                created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                gdrive_synced=f.name in synced_files if synced_files else None,
            ))
    except OSError:
        pass

    return backups


# ── Manual trigger ───────────────────────────────────────────────────────

@router.post("/trigger", response_model=BackupTriggerOut, status_code=status.HTTP_202_ACCEPTED, summary="Trigger manual backup")
async def trigger_backup(current_user=Depends(_super_admin_only)):
    trigger_file = BACKUP_DIR / ".trigger"

    # Check if a backup is already in progress
    if trigger_file.exists():
        raise HTTPException(status_code=409, detail="A backup is already in progress")

    try:
        trigger_file.write_text(datetime.now(timezone.utc).isoformat())
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger backup: {e}")

    return BackupTriggerOut(message="Backup triggered. It will start shortly.", status="triggered")


# ── Download endpoint ────────────────────────────────────────────────────

@router.get("/download/{filename}", summary="Download a backup file")
async def download_backup(filename: str, current_user=Depends(_super_admin_only)):
    # Sanitize filename — prevent path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not filename.endswith(".sql.gz"):
        raise HTTPException(status_code=400, detail="Invalid file type")

    filepath = BACKUP_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/gzip",
    )


# ── Notification Recipients CRUD ─────────────────────────────────────────

@router.get("/recipients", response_model=list[RecipientOut], summary="List backup notification recipients")
async def list_recipients(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_super_admin_only),
):
    result = await db.execute(
        select(BackupNotificationRecipient).order_by(BackupNotificationRecipient.email)
    )
    return result.scalars().all()

@router.post("/recipients", response_model=RecipientOut, status_code=status.HTTP_201_CREATED, summary="Add backup notification recipient")
async def add_recipient(
    body: RecipientCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_super_admin_only),
):
    existing = await db.execute(
        select(BackupNotificationRecipient).where(BackupNotificationRecipient.email == body.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already in backup recipient list")
    recipient = BackupNotificationRecipient(email=body.email, label=body.label)
    db.add(recipient)
    await db.flush()
    await db.refresh(recipient)
    return recipient

@router.patch("/recipients/{recipient_id}", response_model=RecipientOut, summary="Toggle backup recipient active status")
async def toggle_recipient(
    recipient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_super_admin_only),
):
    result = await db.execute(
        select(BackupNotificationRecipient).where(BackupNotificationRecipient.id == recipient_id)
    )
    recipient = result.scalar_one_or_none()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    recipient.is_active = not recipient.is_active
    await db.flush()
    await db.refresh(recipient)
    return recipient

@router.delete("/recipients/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove backup notification recipient")
async def delete_recipient(
    recipient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(_super_admin_only),
):
    result = await db.execute(
        select(BackupNotificationRecipient).where(BackupNotificationRecipient.id == recipient_id)
    )
    recipient = result.scalar_one_or_none()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    await db.delete(recipient)
