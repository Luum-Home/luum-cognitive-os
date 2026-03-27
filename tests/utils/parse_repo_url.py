"""Utility module: GitHub repository URL parser.

Python port of tests/_helpers/parse-repo-url.sh.
Can be imported by tests or run standalone.
"""


def parse_repo_url(input_url: str) -> str:
    """Extract owner/repo from a GitHub URL.

    Supports: https://github.com/owner/repo, github.com/owner/repo,
    owner/repo, .git suffix.

    Raises:
        ValueError: If input is empty, non-GitHub, or cannot be parsed.
    """
    if not input_url:
        raise ValueError("empty input")

    cleaned = input_url

    # Strip protocol
    for prefix in ("https://", "http://"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break

    # Strip github.com/ prefix
    if cleaned.startswith("github.com/"):
        cleaned = cleaned[len("github.com/"):]
    else:
        # Check for non-GitHub hosts
        host = cleaned.split("/")[0] if "/" in cleaned else cleaned
        if "." in host and host != "github.com":
            raise ValueError(f"non-GitHub URL: {input_url}")

    # Strip .git suffix
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]

    # Strip trailing slash
    cleaned = cleaned.rstrip("/")

    # Extract owner/repo
    parts = cleaned.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError(f"cannot extract owner/repo from: {input_url}")

    owner = parts[0]
    repo = parts[1]

    # Reject if owner contains dots (likely a hostname)
    if "." in owner and owner != "github.com":
        raise ValueError(f"non-GitHub URL: {input_url}")

    return f"{owner}/{repo}"


if __name__ == "__main__":
    # Self-test
    tests = [
        ("https://github.com/owner/repo", "owner/repo"),
        ("github.com/owner/repo", "owner/repo"),
        ("owner/repo", "owner/repo"),
        ("https://github.com/owner/repo.git", "owner/repo"),
        ("https://github.com/owner/repo/", "owner/repo"),
    ]
    for url, expected in tests:
        result = parse_repo_url(url)
        assert result == expected, f"parse_repo_url({url!r}) = {result!r}, expected {expected!r}"
    print("All self-tests passed.")
