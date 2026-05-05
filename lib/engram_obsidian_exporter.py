# SCOPE: both
"""Engram → Obsidian exporter — read-only graph visualization layer.

FOR (use case)
--------------
Use this module when a maintainer wants a human-readable Obsidian vault export
of Engram observations and typed relations.  Engram remains the authoritative
memory backend; this exporter only renders Markdown files with frontmatter and
wikilinks for navigation/audit.

The default operation is dry-run.  Callers must pass ``write=True`` (or the
wrapper script's ``--write`` flag) before any vault files are created or
modified.

ADR reference: ``docs/adrs/ADR-071-engram-lifecycle-evolution.md`` Phase 4.
Research: ``docs/research/obsidian-doc-graph-ai-agent-memory-2026-05-05.md``.

NOT (cross-reference)
---------------------
This module does NOT import from Obsidian and does NOT mutate Engram.  It reads
Engram observations through typed clients and reads ``memory_relations`` from
SQLite in read-only mode, mirroring ``lib.engram_graph_walker``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LIB_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(_LIB_DIR) not in sys.path:
    sys.path.insert(0, os.path.dirname(_LIB_DIR))

from lib import engram_http_client as _http_default  # noqa: E402
from lib.engram_lifecycle import EngramLifecycle  # noqa: E402

_ENGRAM_DATA_DIR = os.environ.get("ENGRAM_DATA_DIR", os.path.expanduser("~/.engram"))
_DEFAULT_DB_PATH = os.path.join(_ENGRAM_DATA_DIR, "engram.db")
_DEFAULT_OUTPUT_SUBDIR = "Cognitive OS/Engram"
_MAX_FILENAME_CHARS = 96


@dataclass(frozen=True)
class ExportedFile:
    """One planned or written Markdown export."""

    observation_id: str
    sync_id: str
    title: str
    topic_key: str
    path: str
    relation_count: int


@dataclass(frozen=True)
class ExportResult:
    """Summary returned by :meth:`EngramObsidianExporter.export`."""

    dry_run: bool
    vault: str
    output_dir: str
    manifest_path: str
    project: str
    files_planned: int
    files_written: int
    relation_count: int
    exported_files: list[ExportedFile]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["exported_files"] = [asdict(item) for item in self.exported_files]
        return payload


@dataclass(frozen=True)
class Relation:
    """Typed directed Engram relation between two observation sync IDs."""

    source_id: str
    target_id: str
    relation: str
    confidence: float | None = None


class EngramObsidianExporter:
    """Render Engram observations into Obsidian-compatible Markdown.

    Args:
        http_client_module: Injectable Engram HTTP client module for tests.
        db_path:            Path to Engram SQLite DB. Opened read-only.
        lifecycle:          Optional lifecycle parser instance.
        now:                Injectable UTC clock for deterministic tests.
    """

    def __init__(
        self,
        *,
        http_client_module: Any = None,
        db_path: str | None = None,
        lifecycle: EngramLifecycle | None = None,
        now: Any = None,
    ) -> None:
        self._http = http_client_module or _http_default
        self._db_path = db_path or _DEFAULT_DB_PATH
        self._lifecycle = lifecycle or EngramLifecycle()
        self._now = now or (lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    def export(
        self,
        *,
        vault: str | Path,
        project: str = "",
        limit: int = 100,
        since: str = "",
        output_subdir: str = _DEFAULT_OUTPUT_SUBDIR,
        write: bool = False,
        force: bool = False,
    ) -> ExportResult:
        """Plan or perform a one-way Engram → Obsidian export.

        Args:
            vault:         Obsidian vault root. Required even in dry-run mode.
            project:       Optional Engram project filter.
            limit:         Maximum recent observations to export.
            since:         Optional ISO/date lower bound on created/updated time.
            output_subdir: Relative folder under the vault for exported files.
            write:         False means dry-run; True writes files atomically.
            force:         Ignore the incremental manifest and rewrite all planned files.

        Returns:
            ExportResult with planned/written counts. Never mutates Engram.
        """
        vault_path = Path(vault).expanduser()
        if not str(vault_path):
            raise ValueError("vault path is required")
        if vault_path.exists() and not vault_path.is_dir():
            raise ValueError(f"vault path is not a directory: {vault_path}")
        if not vault_path.exists() and not write:
            raise ValueError(f"vault path does not exist: {vault_path}")

        output_dir = vault_path / output_subdir
        manifest_path = output_dir / ".engram-obsidian-export.json"

        observations = self._load_observations(project=project, limit=limit, since=since)
        filename_by_sync = self._filename_map(observations)
        relations = self._load_relations(set(filename_by_sync))
        outgoing = self._group_relations(relations)

        exported: list[ExportedFile] = []
        files_written = 0
        previous_manifest = self._read_manifest(manifest_path) if not force else {}

        rendered: list[tuple[Path, str, dict[str, Any], ExportedFile]] = []
        for obs in observations:
            sync_id = str(obs.get("sync_id") or "")
            filename = filename_by_sync.get(sync_id)
            if not filename:
                continue
            markdown = self.render_observation(
                obs,
                filename_by_sync=filename_by_sync,
                relations=outgoing.get(sync_id, []),
            )
            target = output_dir / filename
            digest = self._content_digest(markdown)
            relation_count = len(outgoing.get(sync_id, []))
            item = ExportedFile(
                observation_id=str(obs.get("id") or ""),
                sync_id=sync_id,
                title=str(obs.get("title") or "Untitled"),
                topic_key=str(obs.get("topic_key") or ""),
                path=str(target),
                relation_count=relation_count,
            )
            exported.append(item)
            rendered.append((target, markdown, {"digest": digest}, item))

        if write:
            output_dir.mkdir(parents=True, exist_ok=True)
            previous_files = previous_manifest.get("files", {}) if isinstance(previous_manifest, dict) else {}
            for target, markdown, metadata, item in rendered:
                old = previous_files.get(target.name, {}) if isinstance(previous_files, dict) else {}
                if not force and old.get("digest") == metadata["digest"] and target.exists():
                    continue
                self._write_atomic(target, markdown)
                files_written += 1
            self._write_manifest(
                manifest_path,
                project=project,
                files=rendered,
                output_dir=output_dir,
                relation_count=len(relations),
            )

        return ExportResult(
            dry_run=not write,
            vault=str(vault_path),
            output_dir=str(output_dir),
            manifest_path=str(manifest_path),
            project=project,
            files_planned=len(exported),
            files_written=files_written,
            relation_count=len(relations),
            exported_files=exported,
        )

    def render_observation(
        self,
        obs: dict[str, Any],
        *,
        filename_by_sync: dict[str, str],
        relations: list[Relation],
    ) -> str:
        """Render a single observation as Markdown with YAML frontmatter."""
        title = str(obs.get("title") or "Untitled")
        content = str(obs.get("content") or "")
        trailer = self._lifecycle._parse_trailer(content)
        base_content = self._lifecycle._strip_trailer(content).rstrip()
        sync_id = str(obs.get("sync_id") or "")

        frontmatter: dict[str, Any] = {
            "cos_observation_id": str(obs.get("id") or ""),
            "sync_id": sync_id,
            "topic_key": str(obs.get("topic_key") or ""),
            "type": str(obs.get("type") or "manual"),
            "project": str(obs.get("project") or ""),
            "created_at": str(obs.get("created_at") or ""),
            "updated_at": str(obs.get("updated_at") or ""),
        }
        if trailer:
            for key in (
                "confidence",
                "reinforcement_count",
                "last_reinforced",
                "decay_class",
                "crystallized",
                "superseded_obs_ids",
            ):
                if key in trailer:
                    frontmatter[key] = trailer[key]

        relation_payload: dict[str, list[str]] = {}
        for rel in relations:
            if rel.target_id in filename_by_sync:
                relation_payload.setdefault(rel.relation, []).append(rel.target_id)
        if relation_payload:
            frontmatter["relations"] = relation_payload

        lines = ["---", self._yaml(frontmatter).rstrip(), "---", "", f"# {title}", ""]
        if base_content:
            lines.extend([base_content, ""])
        if relations:
            link_lines = self._relation_link_lines(relations, filename_by_sync)
            if link_lines:
                lines.extend(["## Engram Relations", "", *link_lines, ""])
        return "\n".join(lines).rstrip() + "\n"

    def _load_observations(self, *, project: str, limit: int, since: str) -> list[dict[str, Any]]:
        try:
            observations = self._http.get_recent(limit=max(1, limit), project=project)
        except Exception:
            observations = []
        if since:
            observations = [obs for obs in observations if self._obs_on_or_after(obs, since)]
        return observations[:limit]

    def _load_relations(self, exported_sync_ids: set[str]) -> list[Relation]:
        if not exported_sync_ids or not os.path.isfile(self._db_path):
            return []
        try:
            uri = f"file:{self._db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            with conn:
                placeholders = ",".join("?" * len(exported_sync_ids))
                rows = conn.execute(
                    f"""
                    SELECT source_id, target_id, relation, confidence
                    FROM memory_relations
                    WHERE judgment_status != 'rejected'
                      AND source_id IN ({placeholders})
                      AND target_id IN ({placeholders})
                      AND source_id IS NOT NULL AND source_id != ''
                      AND target_id IS NOT NULL AND target_id != ''
                    """,
                    [*exported_sync_ids, *exported_sync_ids],
                ).fetchall()
            conn.close()
            return [
                Relation(
                    source_id=str(row[0]),
                    target_id=str(row[1]),
                    relation=str(row[2]),
                    confidence=float(row[3]) if row[3] is not None else None,
                )
                for row in rows
            ]
        except Exception:
            return []

    def _group_relations(self, relations: list[Relation]) -> dict[str, list[Relation]]:
        grouped: dict[str, list[Relation]] = {}
        for rel in relations:
            grouped.setdefault(rel.source_id, []).append(rel)
        for values in grouped.values():
            values.sort(key=lambda r: (r.relation, r.target_id))
        return grouped

    def _filename_map(self, observations: list[dict[str, Any]]) -> dict[str, str]:
        result: dict[str, str] = {}
        used: set[str] = set()
        for obs in observations:
            sync_id = str(obs.get("sync_id") or "")
            if not sync_id:
                continue
            base = self._slug(str(obs.get("topic_key") or obs.get("title") or "observation"))
            prefix = str(obs.get("id") or sync_id[:8] or "obs")
            filename = f"{prefix}-{base}.md"[:_MAX_FILENAME_CHARS]
            if not filename.endswith(".md"):
                filename = filename.rsplit(".", 1)[0] + ".md"
            candidate = filename
            counter = 2
            while candidate in used:
                stem = filename[:-3]
                candidate = f"{stem}-{counter}.md"
                counter += 1
            used.add(candidate)
            result[sync_id] = candidate
        return result

    def _relation_link_lines(
        self, relations: list[Relation], filename_by_sync: dict[str, str]
    ) -> list[str]:
        lines: list[str] = []
        for rel in sorted(relations, key=lambda r: (r.relation, r.target_id)):
            filename = filename_by_sync.get(rel.target_id)
            if not filename:
                continue
            note = filename[:-3]
            relation = rel.relation or "related"
            lines.append(f"- **{relation}**: [[{note}]]")
        return lines

    def _yaml(self, value: Any, indent: int = 0) -> str:
        prefix = " " * indent
        if isinstance(value, dict):
            lines: list[str] = []
            for key in sorted(value):
                item = value[key]
                if isinstance(item, dict):
                    lines.append(f"{prefix}{key}:")
                    lines.append(self._yaml(item, indent + 2).rstrip())
                elif isinstance(item, list):
                    lines.append(f"{prefix}{key}:")
                    for entry in item:
                        lines.append(f"{prefix}  - {self._yaml_scalar(entry)}")
                else:
                    lines.append(f"{prefix}{key}: {self._yaml_scalar(item)}")
            return "\n".join(lines) + "\n"
        return f"{prefix}{self._yaml_scalar(value)}\n"

    def _yaml_scalar(self, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int | float):
            return str(value)
        if value is None:
            return "null"
        return json.dumps(str(value), ensure_ascii=False)

    def _slug(self, text: str) -> str:
        slug = text.lower().replace("/", "-")
        slug = re.sub(r"[^a-z0-9._-]+", "-", slug)
        slug = re.sub(r"-+", "-", slug).strip("-._")
        return slug or "observation"

    def _obs_on_or_after(self, obs: dict[str, Any], since: str) -> bool:
        cutoff = self._parse_date(since)
        if cutoff is None:
            return True
        for key in ("updated_at", "created_at"):
            stamp = obs.get(key)
            if not stamp:
                continue
            parsed = self._parse_date(str(stamp))
            if parsed is not None and parsed >= cutoff:
                return True
        return False

    def _parse_date(self, value: str) -> datetime | None:
        try:
            text = value.strip()
            if len(text) == 10 and text[4] == "-":
                return datetime.fromisoformat(text)
            if text.endswith("Z"):
                text = text[:-1]
            return datetime.fromisoformat(text)
        except Exception:
            return None

    def _content_digest(self, content: str) -> str:
        import hashlib

        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _read_manifest(self, manifest_path: Path) -> dict[str, Any]:
        try:
            if manifest_path.exists():
                return json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return {}

    def _write_manifest(
        self,
        manifest_path: Path,
        *,
        project: str,
        files: list[tuple[Path, str, dict[str, Any], ExportedFile]],
        output_dir: Path,
        relation_count: int,
    ) -> None:
        payload = {
            "generated_at": self._now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "project": project,
            "output_dir": str(output_dir),
            "relation_count": relation_count,
            "files": {
                target.name: {
                    "digest": metadata["digest"],
                    "observation_id": item.observation_id,
                    "sync_id": item.sync_id,
                    "topic_key": item.topic_key,
                }
                for target, _markdown, metadata, item in files
            },
        }
        self._write_atomic(manifest_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _write_atomic(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(content)
            tmp_name = handle.name
        os.replace(tmp_name, path)


def _cli_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export Engram observations to an Obsidian vault.")
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault root")
    parser.add_argument("--project", default="", help="Filter to one Engram project")
    parser.add_argument("--limit", type=int, default=100, help="Maximum observations to export")
    parser.add_argument("--since", default="", help="Only export observations on/after date or ISO timestamp")
    parser.add_argument("--output-subdir", default=_DEFAULT_OUTPUT_SUBDIR, help="Vault-relative export folder")
    parser.add_argument("--write", action="store_true", help="Write files. Omit for dry-run.")
    parser.add_argument("--force", action="store_true", help="Rewrite files even if manifest digest is unchanged")
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    args = parser.parse_args(argv)

    result = EngramObsidianExporter().export(
        vault=args.vault,
        project=args.project,
        limit=args.limit,
        since=args.since,
        output_subdir=args.output_subdir,
        write=args.write,
        force=args.force,
    )
    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        mode = "DRY-RUN" if result.dry_run else "WRITE"
        print(
            f"[{mode}] planned={result.files_planned} written={result.files_written} "
            f"relations={result.relation_count} output={result.output_dir}"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_cli_main())
