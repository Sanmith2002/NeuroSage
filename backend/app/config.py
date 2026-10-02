"""Environment settings for the AD co-pathology service."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_DIR = Path(__file__).resolve().parent.parent
VERSION = '1.0.0'


def default_models_dir() -> Path:
    """The trained Stage 4 bundles live in the repo-root models/ folder, next to backend/ and frontend/."""
    return SERVICE_DIR.parent / 'models'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=SERVICE_DIR / '.env', extra='ignore')

    models_dir: Path = Field(default_factory=default_models_dir)
    nacc_model: Literal['auto', 'rf', 'xgb'] = 'auto'
    load_mri: bool = True
    load_bio_fusion: bool = False          # the optional 330 MB MedicalNet ad_bio fusion bundle
    cors_origins: str = 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173'
    api_key: str | None = None
    demo_dir: Path | None = None
    cache_dir: Path = SERVICE_DIR / '.cache'   # MNI template + HD-BET work dirs
    hd_bet_device: str = 'cpu'
    shap_cache_size: int = 256
    artifact_ttl_s: int = 1800

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(',') if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_threads() -> None:
    """Spec §6.6 / §9: let ITK and BLAS use every CPU we were given."""
    n = str(os.cpu_count() or 1)
    os.environ.setdefault('OMP_NUM_THREADS', n)
    os.environ.setdefault('ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS', n)
