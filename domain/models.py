from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class RemoteLaw:
    source_id: str
    title: str
    source_url: str
    status: str | None = None
    promulgation_date: str | None = None
    effective_date: str | None = None
    issuing_authority: str | None = None
    category: str | None = None
    file_url: str | None = None
    content_hash: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LocalLawMetadata:
    source_id: str
    title: str
    source_url: str
    status: str | None
    promulgation_date: str | None
    effective_date: str | None
    issuing_authority: str | None
    category: str | None
    file_url: str | None
    content_hash: str | None
    text_path: str
    synced_at: str
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_remote(cls, law: RemoteLaw, text_path: str) -> "LocalLawMetadata":
        return cls(
            source_id=law.source_id,
            title=law.title,
            source_url=law.source_url,
            status=law.status,
            promulgation_date=law.promulgation_date,
            effective_date=law.effective_date,
            issuing_authority=law.issuing_authority,
            category=law.category,
            file_url=law.file_url,
            content_hash=law.content_hash,
            text_path=text_path,
            synced_at=datetime.now(UTC).isoformat(),
            raw_metadata=law.raw_metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
