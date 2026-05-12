from __future__ import annotations


def parse_scores(text: str) -> list[int]:
    scores: list[int] = []
    for part in text.split(","):
        cleaned: str = part.strip()
        if cleaned:
            scores.append(int(cleaned))
    return scores


def score_total(text: str) -> int:
    total: int = 0
    for score in parse_scores(text):
        total = total + score
    return total


def main() -> None:
    print(parse_scores("10, 20,, 5"))
    print(score_total("10, 20,, 5"))


if __name__ == "__main__":
    main()
