"""Zentrale Konfiguration des Autopiloten (liest autopilot/.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

AUTOPILOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = AUTOPILOT_DIR.parent
load_dotenv(AUTOPILOT_DIR / ".env")

TASKS_PATH = REPO_ROOT / "TASKS.md"
SPEC_PATH = REPO_ROOT / "docs" / "PROJECT_SPEC.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
AGENT_PROMPTS_DIR = REPO_ROOT / ".opencode" / "agents"
PROMPTS_DIR = AUTOPILOT_DIR / "prompts"
STATE_DIR = REPO_ROOT / ".autopilot"          # gitignored: Logs + Patches blockierter Tasks
LOG_DIR = STATE_DIR / "logs"
PATCH_DIR = STATE_DIR / "blocked"

# Dateien, die der Coder nie verändern darf. Der Autopilot setzt Änderungen daran zurück.
PROTECTED_PREFIXES = (
    "TASKS.md", "AGENTS.md", "opencode.json", "compose.dev.yml",
    "docs/", "scripts/", "autopilot/", ".opencode/",
)


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    llm_model: str = os.getenv("LLM_MODEL", "qwen3.6:35b")
    llm_api_key: str = os.getenv("LLM_API_KEY", "local")
    llm_timeout_s: int = _int("LLM_TIMEOUT_S", 1800)
    opencode_bin: str = os.getenv("OPENCODE_BIN", "opencode")
    opencode_model: str = os.getenv("OPENCODE_MODEL", "ollama/qwen3.6:35b")
    coder_timeout_min: int = _int("CODER_TIMEOUT_MIN", 45)
    check_timeout_min: int = _int("CHECK_TIMEOUT_MIN", 20)
    check_build: str = os.getenv("CHECK_BUILD", "1")
    max_revisions: int = _int("MAX_REVISIONS", 5)
    max_blocked_in_row: int = _int("MAX_BLOCKED_IN_ROW", 2)
    review_diff_chars: int = _int("REVIEW_DIFF_CHARS", 48000)
    reset_db_on_rollback: bool = os.getenv("RESET_DB_ON_ROLLBACK", "1") == "1"


SETTINGS = Settings()
