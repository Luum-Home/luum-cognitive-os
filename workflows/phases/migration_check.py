"""Phase executor: Database migration validation.

Validates migrations are reversible, checks for breaking changes,
and manages migration lifecycle for Go (goose), Java (Flyway),
and TypeScript (drizzle/typeorm) services.
"""

import os
import subprocess

from lib.shared_phases import BOLD, DIM, GREEN, RED, RESET, YELLOW
from lib.utils import get_service_abs_path


def phase_migration_check(state, step_label: str, service) -> bool:
    """Validate database migration files.

    Checks:
    1. Migration file exists and is well-formed
    2. Migration is reversible (has down/rollback)
    3. No breaking changes (column drops, type changes without migration)
    """
    lang = service.language
    print(
        f"\n{BOLD}{step_label} Migration check "
        f"({lang} - {service.name})...{RESET}"
    )

    service_abs = get_service_abs_path(service)

    # Detect migration tool and check status
    if lang == "go":
        return _check_goose_migration(state, service_abs)
    elif lang == "spring-boot":
        return _check_flyway_migration(state, service_abs)
    elif lang in ("nestjs", "express"):
        return _check_ts_migration(state, service_abs)

    print(f"  {YELLOW}WARNING{RESET} No migration tool detected for {lang}")
    return True


def _check_goose_migration(state, service_abs: str) -> bool:
    """Check goose migrations (Go services)."""
    migrations_dir = None
    for candidate in [
        os.path.join(service_abs, "migrations"),
        os.path.join(service_abs, "db", "migrations"),
        os.path.join(service_abs, "internal", "db", "migrations"),
    ]:
        if os.path.isdir(candidate):
            migrations_dir = candidate
            break

    if not migrations_dir:
        print(f"  {DIM}No migrations directory found (skipping){RESET}")
        state.update(migration_reversible=True)
        return True

    # Check for new migration files
    migration_files = sorted([
        f for f in os.listdir(migrations_dir)
        if f.endswith(".sql")
    ])

    if not migration_files:
        print(f"  {DIM}No SQL migration files found{RESET}")
        state.update(migration_reversible=True)
        return True

    latest = migration_files[-1]
    latest_path = os.path.join(migrations_dir, latest)
    print(f"  {DIM}Latest migration: {latest}{RESET}")

    # Check if migration has both Up and Down sections
    try:
        with open(latest_path, "r") as f:
            content = f.read()

        has_up = "-- +goose Up" in content
        has_down = "-- +goose Down" in content

        if has_up and has_down:
            state.update(migration_reversible=True)
            print(f"  {GREEN}OK{RESET} Migration is reversible (Up + Down)")
        elif has_up:
            state.update(migration_reversible=False)
            print(
                f"  {YELLOW}WARNING{RESET} Migration has no Down section "
                f"(not reversible)"
            )
        else:
            print(f"  {RED}FAIL{RESET} Migration format is invalid")
            return False

        # Check for potentially breaking changes
        breaking_patterns = [
            "DROP TABLE",
            "DROP COLUMN",
            "ALTER COLUMN",
            "RENAME TABLE",
        ]
        for pattern in breaking_patterns:
            if pattern in content.upper():
                print(
                    f"  {YELLOW}WARNING{RESET} Potentially breaking: "
                    f"found '{pattern}' in migration"
                )

        state.update(migration_file=latest)
        return True

    except Exception as e:
        print(f"  {RED}FAIL{RESET} Could not read migration: {e}")
        return False


def _check_flyway_migration(state, service_abs: str) -> bool:
    """Check Flyway migrations (Spring Boot services)."""
    migrations_dir = None
    for candidate in [
        os.path.join(
            service_abs, "src", "main", "resources", "db", "migration"
        ),
        os.path.join(
            service_abs, "src", "main", "resources", "db", "migrations"
        ),
    ]:
        if os.path.isdir(candidate):
            migrations_dir = candidate
            break

    if not migrations_dir:
        print(f"  {DIM}No Flyway migrations directory found (skipping){RESET}")
        state.update(migration_reversible=True)
        return True

    migration_files = sorted([
        f for f in os.listdir(migrations_dir)
        if f.endswith(".sql") and f.startswith("V")
    ])

    if not migration_files:
        print(f"  {DIM}No Flyway migration files found{RESET}")
        return True

    latest = migration_files[-1]
    print(f"  {DIM}Latest Flyway migration: {latest}{RESET}")

    # Flyway versioned migrations are forward-only by convention
    # Check for undo migrations (U prefix)
    undo_files = [
        f for f in os.listdir(migrations_dir)
        if f.startswith("U") and f.endswith(".sql")
    ]

    state.update(
        migration_file=latest,
        migration_reversible=len(undo_files) > 0,
    )

    if undo_files:
        print(f"  {GREEN}OK{RESET} Undo migration available")
    else:
        print(
            f"  {YELLOW}WARNING{RESET} No undo migration (Flyway default). "
            f"Consider adding a U-prefixed migration."
        )

    return True


def _check_ts_migration(state, service_abs: str) -> bool:
    """Check TypeScript migrations (NestJS/Express services)."""
    migrations_dir = None
    for candidate in [
        os.path.join(service_abs, "migrations"),
        os.path.join(service_abs, "src", "migrations"),
        os.path.join(service_abs, "src", "database", "migrations"),
    ]:
        if os.path.isdir(candidate):
            migrations_dir = candidate
            break

    if not migrations_dir:
        print(
            f"  {DIM}No TypeScript migrations directory found "
            f"(skipping){RESET}"
        )
        state.update(migration_reversible=True)
        return True

    migration_files = sorted([
        f for f in os.listdir(migrations_dir)
        if f.endswith((".ts", ".js"))
    ])

    if not migration_files:
        print(f"  {DIM}No migration files found{RESET}")
        return True

    latest = migration_files[-1]
    latest_path = os.path.join(migrations_dir, latest)
    print(f"  {DIM}Latest migration: {latest}{RESET}")

    # Check if migration has both up and down methods
    try:
        with open(latest_path, "r") as f:
            content = f.read()

        has_up = "async up" in content or "up(" in content
        has_down = "async down" in content or "down(" in content

        if has_up and has_down:
            state.update(migration_reversible=True)
            print(f"  {GREEN}OK{RESET} Migration is reversible (up + down)")
        elif has_up:
            state.update(migration_reversible=False)
            print(
                f"  {YELLOW}WARNING{RESET} Migration has no down method "
                f"(not reversible)"
            )

        state.update(migration_file=latest)
        return True

    except Exception as e:
        print(f"  {RED}FAIL{RESET} Could not read migration: {e}")
        return False
