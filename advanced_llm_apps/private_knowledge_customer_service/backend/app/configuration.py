import json
import os
from pathlib import Path
from threading import RLock
from typing import Any

from app.config import Settings


class ConfigurationStore:
    """Local, permission-restricted configuration overlay for administrator settings."""

    _editable_fields = {
        "knowledge_root",
        "active_provider",
        "deepseek_api_key",
        "deepseek_model",
        "ollama_model",
        "ollama_host",
        "allow_sensitive_cloud",
    }

    def __init__(self, path: Path, defaults: Settings) -> None:
        self.path = path
        self.defaults = defaults
        self._lock = RLock()

    def snapshot(self) -> Settings:
        values = self.defaults.model_dump()
        with self._lock:
            if self.path.exists():
                overlay = json.loads(self.path.read_text(encoding="utf-8"))
                values.update(
                    {key: value for key, value in overlay.items() if key in self._editable_fields}
                )
        return Settings.model_validate(values)

    def update(self, changes: dict[str, Any]) -> Settings:
        with self._lock:
            current = self.snapshot().model_dump()
            current.update(
                {key: value for key, value in changes.items() if key in self._editable_fields}
            )
            editable = {key: current[key] for key in self._editable_fields}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            temporary.write_text(
                json.dumps(editable, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            os.chmod(temporary, 0o600)
            temporary.replace(self.path)
            os.chmod(self.path, 0o600)
        return self.snapshot()
