#!/usr/bin/env python3
"""Private content audit — ADR-202.

Classifies private content by path without reading secret-never-touch file
contents. This is the conservative Slice 2a substrate: manifest validation,
path classification, secret-path detection, and unknown .cognitive-os root
reporting.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml  # type: ignore[import]
except Exception:  # pragma: no cover - minimal env fallback only
    yaml = None


SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__"}


@dataclass(frozen=True)
class Classification:
    path: str
    content_class: str
    surface_id: str | None
    kind: str | None
    may_read_content: bool
    matched_pattern: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "class": self.content_class,
            "surface_id": self.surface_id,
            "kind": self.kind,
            "may_read_content": self.may_read_content,
            "matched_pattern": self.matched_pattern,
        }


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "path": self.path,
            "message": self.message,
        }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def rel_posix(path: Path, project_dir: Path) -> str:
    try:
        rel = path.resolve().relative_to(project_dir.resolve())
    except ValueError:
        rel = path
    text = rel.as_posix()
    return text[2:] if text.startswith("./") else text


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"private-content manifest not found: {path}")
    if yaml is None:
        raise RuntimeError("PyYAML is required to read private-content manifest")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict) or data.get("schema_version") != "private-content/v1":
        raise ValueError(f"invalid private-content manifest: {path}")
    if "classes" not in data or "surfaces" not in data:
        raise ValueError(f"private-content manifest missing classes/surfaces: {path}")
    return data


def _matches(path: str, pattern: str) -> bool:
    normalized = path[2:] if path.startswith("./") else path
    pat = pattern[2:] if pattern.startswith("./") else pattern
    return fnmatch.fnmatchcase(normalized, pat) or fnmatch.fnmatchcase(Path(normalized).name, pat)


def _class_cfg(manifest: dict[str, Any], content_class: str) -> dict[str, Any]:
    classes = manifest.get("classes", {}) or {}
    cfg = classes.get(content_class)
    if not isinstance(cfg, dict):
        raise ValueError(f"unknown private-content class in manifest: {content_class}")
    return cfg


def classify_path(path: str | Path, manifest: dict[str, Any], project_dir: Path | None = None) -> Classification:
    root = project_dir or repo_root()
    if isinstance(path, Path):
        rel = rel_posix(path, root)
    else:
        text = str(path)
        rel = text[2:] if text.startswith("./") else text

    for pattern in manifest.get("secret_patterns", []) or []:
        if _matches(rel, str(pattern)):
            cfg = _class_cfg(manifest, "secret-never-touch")
            return Classification(rel, "secret-never-touch", "secret-pattern", "secret", bool(cfg.get("may_read_content")), str(pattern))

    # Most-specific surface wins so strategy/plans/etc. override the broad root.
    surfaces = list(manifest.get("surfaces", []) or [])
    surfaces.sort(key=lambda surface: max((len(str(p)) for p in surface.get("path_globs", []) or [""]), default=0), reverse=True)
    for surface in surfaces:
        for pattern in surface.get("path_globs", []) or []:
            if _matches(rel, str(pattern)):
                content_class = str(surface.get("class"))
                cfg = _class_cfg(manifest, content_class)
                return Classification(rel, content_class, str(surface.get("id")), str(surface.get("kind")), bool(cfg.get("may_read_content")), str(pattern))

    default_class = str((manifest.get("defaults", {}) or {}).get("unknown_private_content", "local-only"))
    cfg = _class_cfg(manifest, default_class)
    return Classification(rel, default_class, None, "unknown", bool(cfg.get("may_read_content")), None)


def iter_paths(project_dir: Path) -> Iterable[Path]:
    for path in project_dir.rglob("*"):
        rel_parts = path.relative_to(project_dir).parts
        if any(part in SKIP_DIRS for part in rel_parts):
            if path.is_dir():
                continue
            continue
        yield path


def secret_path_findings(project_dir: Path, manifest: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_paths(project_dir):
        classification = classify_path(path, manifest, project_dir)
        if classification.content_class == "secret-never-touch":
            findings.append(
                Finding(
                    code="secret-path-classified",
                    severity="info",
                    path=classification.path,
                    message="Path is classified as secret-never-touch; generic audit did not read content.",
                )
            )
    return findings


def unknown_surface_findings(project_dir: Path, manifest: dict[str, Any]) -> list[Finding]:
    cognitive_root = project_dir / ".cognitive-os"
    if not cognitive_root.exists():
        return []
    declared = {str(item).rstrip("/") for item in manifest.get("declared_private_roots", []) or []}
    findings: list[Finding] = []
    for child in sorted(p for p in cognitive_root.iterdir() if p.is_dir()):
        rel = rel_posix(child, project_dir)
        if rel not in declared:
            findings.append(
                Finding(
                    code="unknown-private-root",
                    severity="warn",
                    path=rel,
                    message=".cognitive-os root exists on disk but is not declared in manifests/private-content.yaml.",
                )
            )
    return findings


def validate_manifest(manifest: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    classes = manifest.get("classes", {}) or {}
    for surface in manifest.get("surfaces", []) or []:
        content_class = surface.get("class")
        if content_class not in classes:
            findings.append(
                Finding(
                    code="unknown-class",
                    severity="block",
                    path=str(surface.get("id", "<unknown>")),
                    message=f"Surface references undefined class: {content_class}",
                )
            )
        for required in ("id", "kind", "path_globs", "class", "audit_metric"):
            if required not in surface:
                findings.append(
                    Finding(
                        code="surface-missing-required-field",
                        severity="block",
                        path=str(surface.get("id", "<unknown>")),
                        message=f"Surface is missing required field: {required}",
                    )
                )
    return findings


def build_report(project_dir: Path, manifest_path: Path, include_unknown: bool = False, include_secrets: bool = False) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    findings = validate_manifest(manifest)
    if include_unknown:
        findings.extend(unknown_surface_findings(project_dir, manifest))
    if include_secrets:
        findings.extend(secret_path_findings(project_dir, manifest))

    surfaces = manifest.get("surfaces", []) or []
    return {
        "schema_version": "private-content-audit/v1",
        "project_dir": str(project_dir),
        "manifest": str(manifest_path),
        "surface_count": len(surfaces),
        "classes": sorted((manifest.get("classes", {}) or {}).keys()),
        "findings": [finding.to_dict() for finding in findings],
        "summary": {
            "block": sum(1 for finding in findings if finding.severity == "block"),
            "warn": sum(1 for finding in findings if finding.severity == "warn"),
            "info": sum(1 for finding in findings if finding.severity == "info"),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit ADR-202 private-content portability classification.")
    parser.add_argument("--project-dir", type=Path, default=repo_root())
    parser.add_argument("--manifest", type=Path, default=repo_root() / "manifests" / "private-content.yaml")
    parser.add_argument("--classify", help="Classify one path and exit")
    parser.add_argument("--unknown-surfaces", action="store_true", help="Report unmanifested .cognitive-os roots")
    parser.add_argument("--scan-secret-paths", action="store_true", help="Report secret-never-touch paths by name without reading contents")
    parser.add_argument("--strict", action="store_true", help="Exit 2 on block or warn findings")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        project_dir = args.project_dir.resolve()
        manifest_path = args.manifest if args.manifest.is_absolute() else (project_dir / args.manifest).resolve()
        manifest = load_manifest(manifest_path)
        if args.classify:
            result = classify_path(args.classify, manifest, project_dir)
            payload: dict[str, Any] = {"status": "ok", "classification": result.to_dict()}
            exit_code = 0
        else:
            payload = build_report(project_dir, manifest_path, args.unknown_surfaces, args.scan_secret_paths)
            summary = payload["summary"]
            exit_code = 2 if args.strict and (summary["block"] or summary["warn"]) else 0
    except Exception as exc:
        payload = {"status": "error", "message": str(exc)}
        exit_code = 1

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if "classification" in payload:
            item = payload["classification"]
            print(f"{item['path']}: {item['class']} ({item.get('surface_id') or 'default'})")
        else:
            summary = payload.get("summary", {})
            print(f"private-content audit: block={summary.get('block', 0)} warn={summary.get('warn', 0)} info={summary.get('info', 0)}")
            for finding in payload.get("findings", [])[:20]:
                print(f"{finding['severity'].upper()} {finding['code']} {finding['path']}: {finding['message']}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
