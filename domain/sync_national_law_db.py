from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from pathlib import Path

from domain.clients.national_law_db import NationalLawDbClient
from domain.config import load_settings
from domain.extractors import UnsupportedDocumentError, extract_text_from_download
from domain.models import LocalLawMetadata, RemoteLaw
from domain.storage import LawStorage
from domain.text import normalize_text, slugify_title


LOGGER = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synchronize National Law DB legislation locally.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare remote and local metadata without writing; exit 2 when changes exist.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Discover and compare without writing laws.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of discovered laws to process.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rewrite local law files even when metadata/content hash has not changed.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    settings = load_settings()
    storage = LawStorage(settings.laws_dir, settings.state_dir)
    storage.prepare()
    settings.tmp_dir.mkdir(parents=True, exist_ok=True)

    client = NationalLawDbClient(settings)
    index = storage.load_index()

    dry_run = args.dry_run or args.check
    stats = {"seen": 0, "created": 0, "updated": 0, "skipped": 0, "failed": 0}
    for remote in client.iter_laws():
        if args.limit is not None and stats["seen"] >= args.limit:
            break
        stats["seen"] += 1
        try:
            changed = sync_one(remote, client, storage, index, settings.tmp_dir, dry_run, args.force)
            if changed == "created":
                stats["created"] += 1
            elif changed == "updated":
                stats["updated"] += 1
            else:
                stats["skipped"] += 1
        except Exception:
            stats["failed"] += 1
            LOGGER.exception("Failed to sync law: %s", remote.title)

    if not dry_run:
        storage.save_index(index)

    LOGGER.info("Sync finished: %s", stats)
    if args.check and stats["failed"]:
        return 1
    if args.check and (stats["created"] or stats["updated"]):
        return 2
    return 1 if stats["failed"] else 0


def sync_one(
    remote: RemoteLaw,
    client: NationalLawDbClient,
    storage: LawStorage,
    index: dict[str, dict],
    tmp_dir: Path,
    dry_run: bool,
    force: bool,
) -> str:
    local = index.get(remote.source_id)
    detailed, inline_text = client.fetch_detail(remote)

    if local and not force and not has_changed(local, detailed):
        LOGGER.info("Skipped unchanged law: %s", detailed.title)
        return "skipped"

    action = "updated" if local else "created"
    LOGGER.info("%s law: %s", action.capitalize(), detailed.title)
    if dry_run:
        return action

    text = inline_text
    if not text and detailed.file_url:
        tmp_path = tmp_dir / f"{slugify_title(detailed.title)}{guess_suffix(detailed.file_url)}"
        content_type = client.download_file(detailed.file_url, tmp_path)
        try:
            text = extract_text_from_download(tmp_path, content_type)
        finally:
            tmp_path.unlink(missing_ok=True)

    if not text:
        raise UnsupportedDocumentError(f"No extractable text found for {detailed.title}")

    text = normalize_text(text)
    metadata = LocalLawMetadata.from_remote(
        replace(detailed, content_hash=detailed.content_hash or hash_text(text)),
        text_path="",
    )
    law_dir = storage.write_law(metadata, text)
    index[detailed.source_id] = {
        **metadata.to_dict(),
        "folder": str(law_dir.relative_to(storage.laws_dir.parent)),
    }
    return action


def has_changed(local: dict, remote: RemoteLaw) -> bool:
    comparable_fields = (
        "title",
        "source_url",
        "status",
        "promulgation_date",
        "effective_date",
        "issuing_authority",
        "category",
        "file_url",
        "content_hash",
    )
    return any(local.get(field) != getattr(remote, field) for field in comparable_fields)


def guess_suffix(url: str) -> str:
    clean_url = url.lower().split("?", 1)[0]
    for suffix in (".pdf", ".txt", ".text"):
        if clean_url.endswith(suffix):
            return suffix
    return ".download"


def hash_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
