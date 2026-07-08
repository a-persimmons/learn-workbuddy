from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .config import HarnessConfig


GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class AuditEntry:
    index: int
    timestamp: int
    action: str
    data: dict[str, Any]
    prev_hash: str
    hash: str


class AuditLog:
    """Append-only hash chain for high-risk harness events."""

    def __init__(self, config: HarnessConfig) -> None:
        self.config = config
        self.config.ensure_dirs()
        self.path = self.config.audit_dir / "audit.jsonl"

    def append(self, action: str, data: dict[str, Any]) -> AuditEntry:
        entries = self.read_entries()
        prev_hash = entries[-1].hash if entries else GENESIS_HASH
        index = len(entries) + 1
        timestamp = int(time.time() * 1000)
        digest = self._hash_payload(index, timestamp, action, data, prev_hash)
        entry = AuditEntry(
            index=index,
            timestamp=timestamp,
            action=action,
            data=data,
            prev_hash=prev_hash,
            hash=digest,
        )
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.__dict__, ensure_ascii=False, sort_keys=True) + "\n")
        return entry

    def read_entries(self) -> list[AuditEntry]:
        if not self.path.exists():
            return []
        entries: list[AuditEntry] = []
        for line in self._read_lines():
            if not line.strip():
                continue
            data = json.loads(line)
            entries.append(AuditEntry(**data))
        return entries

    def verify(self) -> bool:
        try:
            prev_hash = GENESIS_HASH
            for expected_index, entry in enumerate(self.read_entries(), start=1):
                if entry.index != expected_index or entry.prev_hash != prev_hash:
                    return False
                digest = self._hash_payload(
                    entry.index,
                    entry.timestamp,
                    entry.action,
                    entry.data,
                    entry.prev_hash,
                )
                if digest != entry.hash:
                    return False
                prev_hash = entry.hash
            return True
        except (OSError, json.JSONDecodeError, TypeError):
            return False

    def _read_lines(self) -> Iterable[str]:
        return self.path.read_text(encoding="utf-8").splitlines()

    def _hash_payload(
        self,
        index: int,
        timestamp: int,
        action: str,
        data: dict[str, Any],
        prev_hash: str,
    ) -> str:
        payload = {
            "index": index,
            "timestamp": timestamp,
            "action": action,
            "data": data,
            "prev_hash": prev_hash,
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
