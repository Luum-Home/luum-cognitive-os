from __future__ import annotations


def weighted_sum(values: list[int]) -> int:
    total: int = 0
    for index in range(len(values)):
        total = total + values[index] * (index + 1)
    return total


def normalize_positive(values: list[int]) -> list[int]:
    output: list[int] = []
    for value in values:
        if value > 0:
            output.append(value)
        else:
            output.append(0)
    return output


def main() -> None:
    values: list[int] = [3, -2, 5, 0]
    print(weighted_sum(values))
    print(normalize_positive(values))


if __name__ == "__main__":
    main()
