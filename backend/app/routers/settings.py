"""Settings API router — CRUD for AI API configuration."""

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import Settings, get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsRead(BaseModel):
    base_url: str = ""
    api_key: str = ""
    model_name: str = "gpt-4"
    api_key_masked: str = ""


class SettingsUpdate(BaseModel):
    base_url: str | None = None
    api_key: str | None = None
    model_name: str | None = None


def _load_config(settings: Settings) -> dict:
    """Load config from disk."""
    config_path = settings.config_path
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {"base_url": "", "api_key": "", "model_name": "gpt-4"}


def _save_config(settings: Settings, config: dict) -> None:
    """Save config to disk."""
    config_path = settings.config_path
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def _mask_key(key: str) -> str:
    """Mask the API key for display."""
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


@router.get("", response_model=SettingsRead)
def get_settings_endpoint(
    settings: Settings = Depends(get_settings),
):
    """Get current API settings (key masked)."""
    config = _load_config(settings)
    return SettingsRead(
        base_url=config.get("base_url", ""),
        api_key=config.get("api_key", ""),
        model_name=config.get("model_name", "gpt-4"),
        api_key_masked=_mask_key(config.get("api_key", "")),
    )


@router.put("", response_model=SettingsRead)
def update_settings(
    data: SettingsUpdate,
    settings: Settings = Depends(get_settings),
):
    """Update API settings."""
    config = _load_config(settings)

    if data.base_url is not None:
        config["base_url"] = data.base_url
    if data.api_key is not None:
        config["api_key"] = data.api_key
    if data.model_name is not None:
        config["model_name"] = data.model_name

    _save_config(settings, config)

    return SettingsRead(
        base_url=config.get("base_url", ""),
        api_key=config.get("api_key", ""),
        model_name=config.get("model_name", "gpt-4"),
        api_key_masked=_mask_key(config.get("api_key", "")),
    )
