"""
tests/unit/test_bootstrap.py
Tests for the bootstrap logic functions used by cos-bootstrap.sh and cos-update.sh.

These tests exercise the core logic (env merging, key generation, directory creation)
without starting Docker or any external services.
"""
import os
import subprocess
import tempfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers that mirror the shell script logic in Python for testing
# ---------------------------------------------------------------------------

def env_get(env_file: Path, key: str) -> str:
    """Read a key's value from an env file. Returns '' if not found."""
    for line in env_file.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line[len(key) + 1:]
    return ""


def env_set(env_file: Path, key: str, value: str) -> None:
    """Write or update a key in an env file."""
    lines = env_file.read_text().splitlines()
    new_lines = []
    found = False
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    env_file.write_text("\n".join(new_lines) + "\n")


def merge_env(example: Path, target: Path) -> tuple[int, int]:
    """
    Merge new vars from example into target.
    Returns (added_count, preserved_count).
    Never overwrites existing values.
    """
    existing_keys: set[str] = set()
    if target.exists():
        for line in target.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                existing_keys.add(line.split("=", 1)[0])

    added = 0
    preserved = 0
    new_lines: list[str] = []

    for line in example.read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0]
            if key in existing_keys:
                preserved += 1
                continue  # skip — already present
            new_lines.append(line)
            added += 1

    if new_lines and target.exists():
        with target.open("a") as f:
            f.write("\n" + "\n".join(new_lines) + "\n")
    elif new_lines:
        target.write_text("\n".join(new_lines) + "\n")

    return added, preserved


def generate_encryption_key() -> str:
    """Generate a 64-char hex string (32 random bytes)."""
    return os.urandom(32).hex()


def create_cos_directory_structure(cos_dir: Path) -> list[Path]:
    """Create the .cognitive-os/ directory structure. Returns list of created dirs."""
    dirs = [
        cos_dir / "sessions",
        cos_dir / "metrics",
        cos_dir / "tasks",
        cos_dir / "checkpoints",
        cos_dir / "plans" / "features",
        cos_dir / "plans" / "bugs",
        cos_dir / "plans" / "chores",
        cos_dir / "plans" / "migrations",
        cos_dir / "dynamic-tools",
        cos_dir / "workflows" / "steps",
    ]
    created = []
    for d in dirs:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(d)
    return created


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEnvMerge:
    """Tests for the env-merge logic."""

    def test_env_merge_preserves_existing_values(self, tmp_path):
        """Existing .env values must never be overwritten during merge."""
        example = tmp_path / "env.example"
        example.write_text(
            "ANTHROPIC_API_KEY=\n"
            "LANGFUSE_PG_USER=langfuse\n"
            "LANGFUSE_PG_PASS=langfuse_pass\n"
            "NEW_VAR=default_value\n"
        )

        target = tmp_path / ".env"
        target.write_text(
            "ANTHROPIC_API_KEY=my-real-key\n"
            "LANGFUSE_PG_USER=custom_user\n"
            "LANGFUSE_PG_PASS=super_secret\n"
        )

        added, preserved = merge_env(example, target)

        # Original values must be intact
        assert env_get(target, "ANTHROPIC_API_KEY") == "my-real-key", \
            "ANTHROPIC_API_KEY was overwritten — existing values must be preserved"
        assert env_get(target, "LANGFUSE_PG_USER") == "custom_user", \
            "LANGFUSE_PG_USER was overwritten"
        assert env_get(target, "LANGFUSE_PG_PASS") == "super_secret", \
            "LANGFUSE_PG_PASS was overwritten"

        # NEW_VAR was not in target, so it should have been added
        assert env_get(target, "NEW_VAR") == "default_value", \
            "NEW_VAR should have been added from example"

        assert added == 1
        assert preserved == 3

    def test_env_merge_adds_new_vars(self, tmp_path):
        """New variables from env.example must be added to the target .env."""
        example = tmp_path / "env.example"
        example.write_text(
            "EXISTING_KEY=old_value\n"
            "NEW_KEY_A=value_a\n"
            "NEW_KEY_B=value_b\n"
            "ANOTHER_NEW=value_c\n"
        )

        target = tmp_path / ".env"
        target.write_text("EXISTING_KEY=my_custom_value\n")

        added, preserved = merge_env(example, target)

        assert added == 3, f"Expected 3 new vars added, got {added}"
        assert preserved == 1, f"Expected 1 var preserved, got {preserved}"

        assert env_get(target, "NEW_KEY_A") == "value_a"
        assert env_get(target, "NEW_KEY_B") == "value_b"
        assert env_get(target, "ANOTHER_NEW") == "value_c"
        assert env_get(target, "EXISTING_KEY") == "my_custom_value"  # unchanged

    def test_env_merge_with_empty_target(self, tmp_path):
        """If .env doesn't exist yet, all vars from example are added."""
        example = tmp_path / "env.example"
        example.write_text("KEY_ONE=val1\nKEY_TWO=val2\n")

        target = tmp_path / ".env"
        # target does NOT exist

        added, preserved = merge_env(example, target)

        assert added == 2
        assert preserved == 0
        assert target.exists()
        assert env_get(target, "KEY_ONE") == "val1"
        assert env_get(target, "KEY_TWO") == "val2"

    def test_env_merge_skips_comments_and_blank_lines(self, tmp_path):
        """Comments and blank lines in env.example must not be treated as keys."""
        example = tmp_path / "env.example"
        example.write_text(
            "# This is a comment\n"
            "\n"
            "REAL_KEY=real_value\n"
            "# Another comment\n"
            "\n"
        )

        target = tmp_path / ".env"
        target.write_text("")

        added, preserved = merge_env(example, target)

        assert added == 1
        assert env_get(target, "REAL_KEY") == "real_value"


class TestEncryptionKeyGeneration:
    """Tests for LANGFUSE_ENCRYPTION_KEY generation."""

    def test_encryption_key_generation(self):
        """Generated key must be a 64-char hex string."""
        key = generate_encryption_key()
        assert len(key) == 64, f"Key must be 64 chars, got {len(key)}"
        assert all(c in "0123456789abcdef" for c in key), \
            "Key must contain only hex characters"

    def test_encryption_key_is_random(self):
        """Two generated keys must not be equal (with overwhelming probability)."""
        key1 = generate_encryption_key()
        key2 = generate_encryption_key()
        assert key1 != key2, "Two generated keys should not be identical"

    def test_encryption_key_only_set_when_missing(self, tmp_path):
        """bootstrap must not overwrite an existing LANGFUSE_ENCRYPTION_KEY."""
        env_file = tmp_path / ".env"
        existing_key = "a" * 64
        env_file.write_text(f"LANGFUSE_ENCRYPTION_KEY={existing_key}\n")

        # Simulate the bootstrap logic: only set if not present
        current = env_get(env_file, "LANGFUSE_ENCRYPTION_KEY")
        if not current:
            new_key = generate_encryption_key()
            env_set(env_file, "LANGFUSE_ENCRYPTION_KEY", new_key)

        assert env_get(env_file, "LANGFUSE_ENCRYPTION_KEY") == existing_key, \
            "Existing LANGFUSE_ENCRYPTION_KEY must not be overwritten"


class TestDirectoryStructureCreation:
    """Tests for .cognitive-os/ directory structure setup."""

    def test_directory_structure_creation(self, tmp_path):
        """All expected .cognitive-os/ directories must be created."""
        cos_dir = tmp_path / ".cognitive-os"

        created = create_cos_directory_structure(cos_dir)

        expected = [
            cos_dir / "sessions",
            cos_dir / "metrics",
            cos_dir / "tasks",
            cos_dir / "checkpoints",
            cos_dir / "plans" / "features",
            cos_dir / "plans" / "bugs",
            cos_dir / "plans" / "chores",
            cos_dir / "plans" / "migrations",
            cos_dir / "dynamic-tools",
            cos_dir / "workflows" / "steps",
        ]

        for d in expected:
            assert d.is_dir(), f"Directory not created: {d}"

        assert len(created) == len(expected), \
            f"Expected {len(expected)} dirs created, got {len(created)}"

    def test_directory_structure_idempotent(self, tmp_path):
        """Calling create twice must not raise and must not duplicate anything."""
        cos_dir = tmp_path / ".cognitive-os"

        # First call
        created_first = create_cos_directory_structure(cos_dir)
        # Second call — nothing new to create
        created_second = create_cos_directory_structure(cos_dir)

        assert len(created_first) > 0
        assert len(created_second) == 0, \
            "Second run should not create any new directories (all already exist)"

        # Structure is still intact
        assert (cos_dir / "sessions").is_dir()
        assert (cos_dir / "plans" / "features").is_dir()


class TestIdempotentRun:
    """Tests that verify full idempotency of the bootstrap operations."""

    def test_idempotent_env_merge(self, tmp_path):
        """Running env merge twice produces the same result as running it once."""
        example = tmp_path / "env.example"
        example.write_text("KEY_A=val_a\nKEY_B=val_b\nKEY_C=val_c\n")

        target = tmp_path / ".env"
        target.write_text("KEY_A=my_override\n")

        # First merge
        added1, _ = merge_env(example, target)
        content_after_first = target.read_text()

        # Second merge — nothing should change
        added2, _ = merge_env(example, target)
        content_after_second = target.read_text()

        assert added1 == 2  # KEY_B and KEY_C added
        assert added2 == 0  # nothing new to add
        assert content_after_first == content_after_second, \
            "Second merge changed the .env file — not idempotent"

    def test_idempotent_encryption_key(self, tmp_path):
        """Running key generation twice: the second run must preserve the first key."""
        env_file = tmp_path / ".env"
        env_file.write_text("LANGFUSE_ENCRYPTION_KEY=\n")

        def bootstrap_key_step(env_file: Path) -> None:
            current = env_get(env_file, "LANGFUSE_ENCRYPTION_KEY")
            if not current:
                new_key = generate_encryption_key()
                env_set(env_file, "LANGFUSE_ENCRYPTION_KEY", new_key)

        # First run: generates and saves a key
        bootstrap_key_step(env_file)
        key_after_first = env_get(env_file, "LANGFUSE_ENCRYPTION_KEY")
        assert len(key_after_first) == 64

        # Second run: must not change the key
        bootstrap_key_step(env_file)
        key_after_second = env_get(env_file, "LANGFUSE_ENCRYPTION_KEY")
        assert key_after_first == key_after_second, \
            "Second run changed LANGFUSE_ENCRYPTION_KEY — not idempotent"

    def test_idempotent_directory_creation(self, tmp_path):
        """Running directory creation 5 times must not raise or produce duplicates."""
        cos_dir = tmp_path / ".cognitive-os"

        for i in range(5):
            try:
                create_cos_directory_structure(cos_dir)
            except Exception as exc:
                raise AssertionError(
                    f"Directory creation raised on run {i + 1}: {exc}"
                ) from exc

        # All expected dirs still present
        assert (cos_dir / "sessions").is_dir()
        assert (cos_dir / "plans" / "features").is_dir()
        assert (cos_dir / "workflows" / "steps").is_dir()


class TestBootstrapScriptSyntax:
    """Smoke-test that the shell scripts are valid bash syntax."""

    def _script_path(self, name: str) -> Path:
        repo_root = Path(__file__).parent.parent.parent
        return repo_root / "scripts" / name

    def test_cos_bootstrap_syntax(self):
        """cos-bootstrap.sh must pass bash -n (syntax check)."""
        script = self._script_path("cos-bootstrap.sh")
        assert script.exists(), f"Script not found: {script}"
        result = subprocess.run(
            ["bash", "-n", str(script)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, \
            f"cos-bootstrap.sh syntax error:\n{result.stderr}"

    def test_cos_update_syntax(self):
        """cos-update.sh must pass bash -n (syntax check)."""
        script = self._script_path("cos-update.sh")
        assert script.exists(), f"Script not found: {script}"
        result = subprocess.run(
            ["bash", "-n", str(script)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, \
            f"cos-update.sh syntax error:\n{result.stderr}"

    def test_cos_bootstrap_help(self):
        """cos-bootstrap.sh --help must exit 0 and print usage."""
        script = self._script_path("cos-bootstrap.sh")
        result = subprocess.run(
            ["bash", str(script), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, \
            f"--help exited with {result.returncode}:\n{result.stderr}"
        assert "USAGE" in result.stdout or "Usage" in result.stdout, \
            "Expected usage info in --help output"

    def test_cos_update_help(self):
        """cos-update.sh --help must exit 0 and print usage."""
        script = self._script_path("cos-update.sh")
        result = subprocess.run(
            ["bash", str(script), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, \
            f"--help exited with {result.returncode}:\n{result.stderr}"
        assert "USAGE" in result.stdout or "Usage" in result.stdout, \
            "Expected usage info in --help output"
