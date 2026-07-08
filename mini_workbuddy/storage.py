from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import HarnessConfig, workspace_id


@dataclass
class SessionRecord:
    id: str
    cwd: str
    title: str
    created_at: int
    updated_at: int


class Storage:
    def __init__(self, config: HarnessConfig) -> None:
        self.config = config
        self.config.ensure_dirs()

    def create_session(self, cwd: str, title: str = "Untitled") -> SessionRecord:
        now = int(time.time() * 1000)
        record = SessionRecord(id=str(uuid.uuid4()), cwd=cwd, title=title, created_at=now, updated_at=now)
        self.write_session_record(record)
        return record

    def write_session_record(self, record: SessionRecord) -> None:
        self.config.sessions_dir.mkdir(parents=True, exist_ok=True)
        (self.config.sessions_dir / f"{record.id}.json").write_text(
            json.dumps(asdict(record), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def load_session(self, session_id: str) -> SessionRecord:
        path = self.config.sessions_dir / f"{session_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return SessionRecord(**data)

    def list_sessions(self) -> list[SessionRecord]:
        records: list[SessionRecord] = []
        for path in sorted(self.config.sessions_dir.glob("*.json")):
            try:
                records.append(SessionRecord(**json.loads(path.read_text(encoding="utf-8"))))
            except (OSError, json.JSONDecodeError, TypeError):
                continue
        return records

    def transcript_path(self, record: SessionRecord) -> Path:
        project_dir = self.config.projects_dir / workspace_id(record.cwd)
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir / f"{record.id}.jsonl"

    def append_event(self, record: SessionRecord, event: dict[str, Any]) -> None:
        path = self.transcript_path(record)
        envelope = {"timestamp": int(time.time() * 1000), **event}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(envelope, ensure_ascii=False) + "\n")

    def read_transcript(self, record: SessionRecord, limit: int = 1000) -> list[dict[str, Any]]:
        path = self.transcript_path(record)
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
        events: list[dict[str, Any]] = []
        for line in lines:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

    def tool_result_path(self, record: SessionRecord, tool_call_id: str) -> Path:
        base = self.transcript_path(record).with_suffix("")
        path = base / "tool-results"
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{tool_call_id}.txt"

    def append_memory(self, scope: str, content: str) -> Path:
        safe_scope = scope.replace("/", "_").replace(" ", "_") or "workspace"
        path = self.config.memory_dir / f"{safe_scope}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(content.rstrip() + "\n")
        return path

    def read_memory(self, scope: str) -> str:
        safe_scope = scope.replace("/", "_").replace(" ", "_") or "workspace"
        path = self.config.memory_dir / f"{safe_scope}.md"
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")
