#!/usr/bin/env python3
# SCOPE: os-only
"""Probe provider executor authentication without reading credential stores."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

READY = "ready"
AUTH_REQUIRED = "auth_required"
UNSUPPORTED = "unsupported"
UNSAFE = "unsafe"


@dataclass(frozen=True)
class AuthProbeResult:
    provider: str
    mode: str
    status: str
    credential_store_access: str
    command: str | None = None
    reason: str = ""
    cost_mode: str = "unknown"
    allowed_runtime: list[str] | None = None


def _which(binary: str, path: str | None = None) -> str | None:
    return shutil.which(binary, path=path)


def _run_status(command: list[str], *, env: Mapping[str, str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    safe_env = dict(env)
    return subprocess.run(
        command,
        cwd=cwd,
        env=safe_env,
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )


def _api_key_present(env: Mapping[str, str], names: list[str]) -> bool:
    return any(bool(env.get(name, "").strip()) for name in names)


def probe(provider: str, mode: str, *, env: Mapping[str, str] | None = None, path: str | None = None) -> AuthProbeResult:
    env = env or os.environ
    path = path if path is not None else env.get("PATH")

    if provider == "local" and mode == "none":
        return AuthProbeResult(
            provider=provider,
            mode=mode,
            status=READY,
            credential_store_access="none",
            command=None,
            reason="local-command executor requires no provider credentials",
            cost_mode="none",
            allowed_runtime=["host", "container"],
        )

    if provider == "codex":
        if mode == "api-key":
            return AuthProbeResult(
                provider=provider,
                mode=mode,
                status=READY if _api_key_present(env, ["OPENAI_API_KEY", "CODEX_API_KEY"]) else AUTH_REQUIRED,
                credential_store_access="none",
                command=None,
                reason="OPENAI_API_KEY or CODEX_API_KEY present" if _api_key_present(env, ["OPENAI_API_KEY", "CODEX_API_KEY"]) else "OPENAI_API_KEY/CODEX_API_KEY not present",
                cost_mode="api_metered",
                allowed_runtime=["host", "container", "cloud"],
            )
        if mode in {"account-session", "device-login"}:
            codex = _which("codex", path)
            if not codex:
                return AuthProbeResult(
                    provider=provider,
                    mode=mode,
                    status=UNSUPPORTED,
                    credential_store_access="forbidden",
                    reason="codex CLI not found on PATH",
                    cost_mode="subscription_account",
                    allowed_runtime=["host"],
                )
            result = _run_status([codex, "login", "status"], env=env)
            output = f"{result.stdout}\n{result.stderr}".strip()
            logged_in = result.returncode == 0 and "Logged in" in output
            return AuthProbeResult(
                provider=provider,
                mode=mode,
                status=READY if logged_in else AUTH_REQUIRED,
                credential_store_access="forbidden",
                command="codex login status",
                reason="codex CLI reports an authenticated account session" if logged_in else "codex CLI did not report an authenticated account session",
                cost_mode="subscription_account",
                allowed_runtime=["host"] if mode == "account-session" else ["host", "container"],
            )

    if provider == "claude":
        if mode == "api-key":
            return AuthProbeResult(
                provider=provider,
                mode=mode,
                status=READY if _api_key_present(env, ["ANTHROPIC_API_KEY"]) else AUTH_REQUIRED,
                credential_store_access="none",
                command=None,
                reason="ANTHROPIC_API_KEY present" if _api_key_present(env, ["ANTHROPIC_API_KEY"]) else "ANTHROPIC_API_KEY not present",
                cost_mode="api_metered",
                allowed_runtime=["host", "container", "cloud"],
            )
        if mode == "oauth-token":
            return AuthProbeResult(
                provider=provider,
                mode=mode,
                status=READY if _api_key_present(env, ["ANTHROPIC_AUTH_TOKEN"]) else AUTH_REQUIRED,
                credential_store_access="none",
                command=None,
                reason="ANTHROPIC_AUTH_TOKEN present" if _api_key_present(env, ["ANTHROPIC_AUTH_TOKEN"]) else "ANTHROPIC_AUTH_TOKEN not present",
                cost_mode="subscription_account",
                allowed_runtime=["host", "container"],
            )
        if mode in {"account-session", "device-login"}:
            claude = _which("claude", path)
            if not claude:
                return AuthProbeResult(
                    provider=provider,
                    mode=mode,
                    status=UNSUPPORTED,
                    credential_store_access="forbidden",
                    reason="claude CLI not found on PATH",
                    cost_mode="subscription_account",
                    allowed_runtime=["host"],
                )
            version = _run_status([claude, "--version"], env=env)
            if version.returncode != 0:
                return AuthProbeResult(
                    provider=provider,
                    mode=mode,
                    status=UNSUPPORTED,
                    credential_store_access="forbidden",
                    command="claude --version",
                    reason="claude CLI exists but did not respond to --version",
                    cost_mode="subscription_account",
                    allowed_runtime=["host"],
                )
            return AuthProbeResult(
                provider=provider,
                mode=mode,
                status=AUTH_REQUIRED,
                credential_store_access="forbidden",
                command="claude --version",
                reason="claude CLI exists, but COS has no non-invasive account-session status probe yet",
                cost_mode="subscription_account",
                allowed_runtime=["host"] if mode == "account-session" else ["host", "container"],
            )

    if provider == "proxy-gateway" and mode == "proxy-gateway":
        return AuthProbeResult(
            provider=provider,
            mode=mode,
            status=AUTH_REQUIRED,
            credential_store_access="none",
            reason="proxy gateway endpoint and credential are not configured in Phase 3",
            cost_mode="gateway_metered",
            allowed_runtime=["host", "container", "cloud"],
        )

    return AuthProbeResult(
        provider=provider,
        mode=mode,
        status=UNSUPPORTED,
        credential_store_access="forbidden",
        reason=f"unsupported provider/mode combination: {provider}/{mode}",
        cost_mode="unknown",
        allowed_runtime=[],
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = probe(args.provider, args.mode)
    payload = asdict(result)
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"{result.provider}/{result.mode}: {result.status} — {result.reason}")
    return 0 if result.status == READY else 2 if result.status == AUTH_REQUIRED else 3


if __name__ == "__main__":
    raise SystemExit(main())

