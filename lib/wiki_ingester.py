# SCOPE: both
"""wiki_ingester — Layer 1 → Layer 2 ingestion pipeline for the compiled vault.

FOR (use case)
--------------
Use this module when raw sources (URLs, local files, or pasted text) need to be
compiled into structured vault pages under ``docs/04-Concepts/ingested/`` and
registered in the append-only source index at ``docs/08-References/raw/index.jsonl``.

The pipeline is intentionally simple:

  1. Fetch / read raw body.
  2. Redact secrets (regex heuristic — see ``_redact_secrets``).
  3. Hash the body (SHA-256).
  4. Look up hash in the JSONL index; if seen before, return existing entry.
  5. Write compiled Markdown page with standard frontmatter.
  6. Append one line to the JSONL index.
  7. Attempt to save an observation to engram (graceful degradation when absent).

CONTRACT
--------
- All three public ``ingest_*`` methods return ``IngestResult``; they **never raise**
  on engram unavailability — the pipeline continues without it.
- ``IngestResult.claim_id`` is ``None`` when engram is unavailable or save failed.
- ``IngestResult.redacted_secrets_count`` is 0 or a positive integer; never negative.
- The JSONL index is append-only — existing lines are never modified.
- Re-ingesting identical content (same SHA-256) returns the existing ``source_id``
  without writing a duplicate JSONL line or overwriting the existing vault page.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import textwrap
import unicodedata
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex for basic secret redaction.
# Matches long alphanumeric tokens that appear next to key/secret/token labels.
# Intentionally conservative — only redacts when context word is present.
# ---------------------------------------------------------------------------
_SECRET_PATTERN = re.compile(
    r'(?i)(?P<label>(?:key|secret|token|password|passwd|pwd|auth|bearer|api[-_]?key)'
    r'\s*[=:"\s]\s*)'
    r'(?P<value>[A-Za-z0-9+/\-_]{20,})',
)
_REDACT_REPLACEMENT = r'\g<label>[REDACTED]'


def _redact_secrets(text: str) -> tuple[str, int]:
    """Replace suspected secrets in *text* with ``[REDACTED]``.

    Returns ``(redacted_text, count)`` where *count* is the number of
    substitutions made.
    """
    result, count = _SECRET_PATTERN.subn(_REDACT_REPLACEMENT, text)
    return result, count


def _sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _slugify(title: str) -> str:
    """Convert *title* to a URL-safe, lowercase, hyphen-separated slug."""
    # Normalise unicode → ASCII approximation
    title = unicodedata.normalize("NFKD", title)
    title = title.encode("ascii", "ignore").decode("ascii")
    title = title.lower()
    # Replace non-alphanumeric runs with a single hyphen
    title = re.sub(r"[^a-z0-9]+", "-", title)
    title = title.strip("-")
    return title or "untitled"


# ---------------------------------------------------------------------------
# Public data classes
# ---------------------------------------------------------------------------

@dataclass
class RawSource:
    """Represents a registered raw source entry (one line in index.jsonl)."""

    source_id: str          # deterministic: "sha256-{first-16-chars-of-hash}"
    type: str               # "url" | "file" | "text"
    locator: str            # original URL, file path, or "inline"
    sha256_hash: str        # full 64-char hex digest
    page_path: str          # relative path to compiled vault page
    ingested_at: str        # ISO-8601 UTC timestamp


@dataclass
class IngestResult:
    """Returned by every ``WikiIngester.ingest_*`` method."""

    source_id: str
    page_path: Path
    claim_id: int | None = None          # engram observation ID, or None
    redacted_secrets_count: int = 0
    already_existed: bool = False        # True when content hash was already known


# ---------------------------------------------------------------------------
# Core ingester
# ---------------------------------------------------------------------------

class WikiIngester:
    """Ingest sources into the compiled vault.

    Parameters
    ----------
    vault_root:
        Root of the vault (parent of ``docs/``).  Defaults to the project root
        (``Path("docs")`` is resolved relative to *vault_root*).
    raw_index_path:
        Path to the append-only JSONL index.  Defaults to
        ``docs/08-References/raw/index.jsonl``.
    project:
        Engram project scope passed to ``save_observation``.
    """

    def __init__(
        self,
        vault_root: Path | None = None,
        raw_index_path: Path | None = None,
        project: str = "luum-cognitive-os",
    ) -> None:
        if vault_root is None:
            # Resolve relative to this file's location (project root)
            vault_root = Path(__file__).parent.parent
        self.vault_root = Path(vault_root)
        if raw_index_path is None:
            raw_index_path = self.vault_root / "docs" / "08-References" / "raw" / "index.jsonl"
        self.raw_index_path = Path(raw_index_path)
        self.ingested_dir = self.vault_root / "docs" / "04-Concepts" / "ingested"
        self.project = project

        # Ensure directories exist
        self.raw_index_path.parent.mkdir(parents=True, exist_ok=True)
        self.ingested_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public ingestion methods
    # ------------------------------------------------------------------

    def ingest_url(self, url: str, title: str | None = None) -> IngestResult:
        """Fetch *url*, compile a vault page, and register the source.

        Uses Python's stdlib ``urllib`` — no third-party HTTP library required.
        Raises ``urllib.error.URLError`` for network errors (callers decide how
        to handle); all other logic follows the standard pipeline.
        """
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "wiki-ingester/1.0 (vault pipeline)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            raw_bytes = resp.read()

        # Decode best-effort
        try:
            body = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            body = raw_bytes.decode("latin-1", errors="replace")

        if title is None:
            # Extract <title> from HTML if present
            match = re.search(r"<title[^>]*>\s*([^<]+)\s*</title>", body, re.IGNORECASE)
            title = match.group(1).strip() if match else url.split("/")[-1] or "Untitled"

        return self._pipeline(body=body, title=title, source_type="url", locator=url)

    def ingest_file(self, path: Path, title: str | None = None) -> IngestResult:
        """Read a local file (PDF/MD/TXT) and compile a vault page.

        For PDF files the raw bytes are stored; text is extracted best-effort
        via a simple byte-stream read (no heavy PDF parser required for hashing).
        The vault page body will contain the raw text content.
        """
        path = Path(path)
        raw_bytes = path.read_bytes()

        # Best-effort text extraction
        try:
            body = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # Strip null bytes and non-printable chars common in PDFs
            body = raw_bytes.decode("latin-1", errors="replace")
            body = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", body)

        if title is None:
            title = path.stem.replace("_", " ").replace("-", " ").title()

        return self._pipeline(
            body=body,
            title=title,
            source_type="file",
            locator=str(path),
        )

    def ingest_text(
        self,
        text: str,
        title: str,
        locator: str = "inline",
    ) -> IngestResult:
        """Ingest pasted or programmatically-provided text.

        *locator* should identify the origin of the text (e.g. a document name,
        meeting reference, or ``"inline"`` for anonymous pastes).
        """
        return self._pipeline(body=text, title=title, source_type="text", locator=locator)

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    def _pipeline(
        self,
        *,
        body: str,
        title: str,
        source_type: str,
        locator: str,
    ) -> IngestResult:
        """Central ingestion pipeline shared by all public methods."""
        body, redacted_count = _redact_secrets(body)

        sha256 = _sha256_hex(body)
        source_id = f"sha256-{sha256[:16]}"

        # Check deduplication
        existing = self._find_by_hash(sha256)
        if existing is not None:
            return IngestResult(
                source_id=existing["source_id"],
                page_path=self.vault_root / existing["page_path"],
                claim_id=None,
                redacted_secrets_count=redacted_count,
                already_existed=True,
            )

        slug = _slugify(title)
        ingested_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        page_path = self._compose_page(
            source_id=source_id,
            slug=slug,
            title=title,
            body=body,
            source_type=source_type,
            locator=locator,
            sha256=sha256,
            ingested_at=ingested_at,
        )

        raw_source = RawSource(
            source_id=source_id,
            type=source_type,
            locator=locator,
            sha256_hash=sha256,
            page_path=str(page_path.relative_to(self.vault_root)),
            ingested_at=ingested_at,
        )
        self._register_source(raw_source)

        claim_id = self._emit_engram_claim(
            source_id=source_id,
            slug=slug,
            title=title,
            page_path=page_path,
            ingested_at=ingested_at,
        )

        return IngestResult(
            source_id=source_id,
            page_path=page_path,
            claim_id=claim_id,
            redacted_secrets_count=redacted_count,
            already_existed=False,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_by_hash(self, sha256: str) -> dict[str, Any] | None:
        """Return the index entry matching *sha256*, or ``None``."""
        if not self.raw_index_path.exists():
            return None
        with self.raw_index_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("sha256_hash") == sha256:
                    return entry
        return None

    def _register_source(self, source: RawSource) -> None:
        """Append *source* as one JSON line to the raw index."""
        entry = {
            "source_id": source.source_id,
            "type": source.type,
            "locator": source.locator,
            "sha256_hash": source.sha256_hash,
            "page_path": source.page_path,
            "ingested_at": source.ingested_at,
        }
        with self.raw_index_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _compose_page(
        self,
        *,
        source_id: str,
        slug: str,
        title: str,
        body: str,
        source_type: str,
        locator: str,
        sha256: str,
        ingested_at: str,
    ) -> Path:
        """Write the compiled vault page and return its absolute path."""
        page_path = self.ingested_dir / f"{slug}.md"

        # Truncate body for the page to keep pages readable (first 8 000 chars)
        body_preview = body[:8000]
        if len(body) > 8000:
            body_preview += "\n\n… *(content truncated — full source registered in raw index)*"

        frontmatter = textwrap.dedent(f"""\
            ---
            source_id: {source_id}
            source_hash: {sha256}
            ingested_at: {ingested_at}
            source_locator: {locator}
            source_type: {source_type}
            title: "{title}"
            ---
        """)

        content = frontmatter + f"\n# {title}\n\n" + body_preview + "\n"
        page_path.write_text(content, encoding="utf-8")
        return page_path

    def _emit_engram_claim(
        self,
        *,
        source_id: str,
        slug: str,
        title: str,
        page_path: Path,
        ingested_at: str,
    ) -> int | None:
        """Try to save an observation to engram; return claim ID or None.

        Never raises — all errors (import failures, network issues, engram
        daemon unavailability) are caught and logged at DEBUG level.
        """
        try:
            from lib import engram_client  # noqa: PLC0415 — intentional lazy import
        except ImportError:
            logger.debug("engram_client not available — skipping claim emission")
            return None

        content = (
            f"Source ingested into vault.\n"
            f"source_id: {source_id}\n"
            f"page: {page_path}\n"
            f"ingested_at: {ingested_at}"
        )
        try:
            result = engram_client.save_observation(
                title=f"Vault ingest: {title}",
                content=content,
                type_="observation",
                topic_key=f"vault-ingest/{slug}",
                project=self.project,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("engram save_observation failed: %s", exc)
            return None

        if result is None:
            return None
        return result.get("id")
