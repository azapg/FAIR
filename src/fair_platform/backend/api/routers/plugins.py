from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.plugin import Plugin
from fair_platform.backend.api.schema.plugin import PluginCreate, PluginRead, PluginUpdate
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models.user import User, UserRole

router = APIRouter()


@router.post("/", response_model=PluginRead, status_code=status.HTTP_201_CREATED)
def create_plugin(payload: PluginCreate, db: Session = Depends(session_dependency), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin users can manage plugins")

    existing = (
        db.query(Plugin)
        .filter(Plugin.id == payload.id, Plugin.hash == payload.hash)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Plugin with same id and hash already exists")
    plugin = Plugin(
        id=payload.id,
        name=payload.name,
        author=payload.author,
        version=payload.version,
        hash=payload.hash,
        source=payload.source,
        meta=payload.meta,
    )
    db.add(plugin)
    db.commit()
    db.refresh(plugin)
    return plugin


@router.get("/", response_model=List[PluginRead])
def list_plugins(id: str | None = None, db: Session = Depends(session_dependency)):
    q = db.query(Plugin)
    if id:
        q = q.filter(Plugin.id == id)
    return q.all()


@router.get("/id/{plugin_id}/hash/{plugin_hash}", response_model=PluginRead)
def get_plugin(plugin_id: str, plugin_hash: str, db: Session = Depends(session_dependency)):
    plugin = (
        db.query(Plugin)
        .filter(Plugin.id == plugin_id, Plugin.hash == plugin_hash)
        .first()
    )
    if not plugin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not found")
    return plugin


@router.put("/id/{plugin_id}/hash/{plugin_hash}", response_model=PluginRead)
def update_plugin(plugin_id: str, plugin_hash: str, payload: PluginUpdate, db: Session = Depends(session_dependency), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin users can manage plugins")

    plugin = (
        db.query(Plugin)
        .filter(Plugin.id == plugin_id, Plugin.hash == plugin_hash)
        .first()
    )
    if not plugin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not found")

    if payload.name is not None:
        plugin.name = payload.name
    if payload.author is not None:
        plugin.author = payload.author
    if payload.version is not None:
        plugin.version = payload.version
    if payload.source is not None:
        plugin.source = payload.source
    if payload.meta is not None:
        plugin.meta = payload.meta

    db.add(plugin)
    db.commit()
    db.refresh(plugin)
    return plugin


@router.delete("/id/{plugin_id}/hash/{plugin_hash}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plugin(plugin_id: str, plugin_hash: str, db: Session = Depends(session_dependency), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin users can manage plugins")

    plugin = (
        db.query(Plugin)
        .filter(Plugin.id == plugin_id, Plugin.hash == plugin_hash)
        .first()
    )
    if not plugin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not found")
    db.delete(plugin)
    db.commit()
    return None


__all__ = ["router"]

