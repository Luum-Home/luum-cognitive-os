from __future__ import annotations


def count_by_prefix(items: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key: str = item[0]
        if key in counts:
            counts[key] = counts[key] + 1
        else:
            counts[key] = 1
    return counts


def labels(counts: dict[str, int]) -> list[str]:
    output: list[str] = []
    for key in sorted(counts.keys()):
        output.append(key + ":" + str(counts[key]))
    return output


def main() -> None:
    counts: dict[str, int] = count_by_prefix(["alpha", "atom", "beta"])
    print(labels(counts))


if __name__ == "__main__":
    main()
