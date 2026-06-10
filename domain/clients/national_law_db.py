from __future__ import annotations

import hashlib
import re
import time
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from domain.config import Settings
from domain.models import RemoteLaw


class NationalLawDbClient:
    """Client for the National Database of Laws and Regulations.

    The public site has changed its frontend over time, so this client keeps the
    first project version conservative: listing pages are configured with
    NATIONAL_LAW_DB_INDEX_URLS and parsed for law/document links. If the site's
    internal JSON API is later pinned down, add it behind iter_laws().
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.user_agent})

    def iter_laws(self) -> Iterable[RemoteLaw]:
        if not self.settings.index_urls:
            raise ValueError(
                "NATIONAL_LAW_DB_INDEX_URLS is empty. Configure one or more official listing URLs."
            )

        seen: set[str] = set()
        for index_url in self.settings.index_urls:
            response = self._get(index_url)
            soup = BeautifulSoup(response.text, "html.parser")
            for link in soup.select("a[href]"):
                title = link.get_text(" ", strip=True)
                href = link.get("href")
                if not title or not href:
                    continue
                source_url = urljoin(index_url, href)
                if source_url in seen:
                    continue
                seen.add(source_url)
                yield RemoteLaw(
                    source_id=stable_source_id(source_url),
                    title=title,
                    source_url=source_url,
                    file_url=source_url if looks_like_document_url(source_url) else None,
                    raw_metadata={"discovered_from": index_url},
                )

    def fetch_detail(self, law: RemoteLaw) -> tuple[RemoteLaw, str | None]:
        response = self._get(law.source_url)
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        content_hash = hashlib.sha256(response.content).hexdigest()

        if content_type == "application/pdf" or law.source_url.lower().endswith(".pdf"):
            return (
                RemoteLaw(
                    **{
                        **law.__dict__,
                        "file_url": law.file_url or law.source_url,
                        "content_hash": content_hash,
                    }
                ),
                None,
            )

        soup = BeautifulSoup(response.text, "html.parser")
        text = extract_main_text(soup)
        file_url = law.file_url or find_document_url(soup, law.source_url)
        metadata = extract_metadata(soup)
        enriched = RemoteLaw(
            **{
                **law.__dict__,
                "title": metadata.get("title") or law.title,
                "status": metadata.get("status") or law.status,
                "promulgation_date": metadata.get("promulgation_date") or law.promulgation_date,
                "effective_date": metadata.get("effective_date") or law.effective_date,
                "issuing_authority": metadata.get("issuing_authority") or law.issuing_authority,
                "category": metadata.get("category") or law.category,
                "file_url": file_url,
                "content_hash": content_hash,
                "raw_metadata": {
                    **law.raw_metadata,
                    "detail_content_type": content_type,
                    "detail_metadata": metadata,
                },
            }
        )
        return enriched, text

    def download_file(self, url: str, target_path: Path) -> str | None:
        response = self._get(url)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(response.content)
        return response.headers.get("content-type", "").split(";")[0].strip().lower() or None

    def _get(self, url: str) -> requests.Response:
        if self.settings.request_delay_seconds > 0:
            time.sleep(self.settings.request_delay_seconds)
        response = self.session.get(url, timeout=self.settings.request_timeout_seconds)
        response.raise_for_status()
        return response


def stable_source_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def looks_like_document_url(url: str) -> bool:
    return url.lower().split("?", 1)[0].endswith((".pdf", ".txt", ".text"))


def find_document_url(soup: BeautifulSoup, base_url: str) -> str | None:
    for link in soup.select("a[href]"):
        href = link.get("href") or ""
        if looks_like_document_url(href):
            return urljoin(base_url, href)
    return None


def extract_main_text(soup: BeautifulSoup) -> str:
    for selector in ("main", "article", ".content", ".detail", "#content"):
        node = soup.select_one(selector)
        if node:
            return node.get_text("\n", strip=True)
    return soup.get_text("\n", strip=True)


def extract_metadata(soup: BeautifulSoup) -> dict[str, str]:
    metadata: dict[str, str] = {}
    title_node = soup.select_one("h1") or soup.select_one("title")
    if title_node:
        metadata["title"] = clean_value(title_node.get_text(" ", strip=True))

    text = soup.get_text("\n", strip=True)
    label_map = {
        "status": ("时效性", "效力状态", "状态"),
        "promulgation_date": ("公布日期", "发布日期", "颁布日期"),
        "effective_date": ("施行日期", "实施日期", "生效日期"),
        "issuing_authority": ("制定机关", "发布机关", "颁布机关"),
        "category": ("法律性质", "类别", "法规类别", "法律部门"),
    }
    for field, labels in label_map.items():
        for label in labels:
            value = find_labeled_value(text, label)
            if value:
                metadata[field] = value
                break
    return metadata


def find_labeled_value(text: str, label: str) -> str | None:
    pattern = rf"{re.escape(label)}\s*[:：]\s*([^\n\r]+)"
    match = re.search(pattern, text)
    if not match:
        return None
    return clean_value(match.group(1))


def clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" \t\r\n-_|")
