from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'envaplast.db'}")
    seed: int = int(os.getenv("ENVAPLAST_SEED", "20260720"))
    environment: str = os.getenv("ENVAPLAST_ENV", "development")


settings = Settings()
